from typing import List, Optional
from bson import ObjectId
from datetime import datetime, timezone
from app.db.mongodb import get_database
from app.models.resume import ResumeInDB, ResumeVersion, ResumeCreate, ResumeStatus
from app.models.user import PyObjectId, UserRole

class ResumeService:
    @staticmethod
    async def create_resume(user_id: PyObjectId, resume_in: ResumeCreate) -> ResumeInDB:
        db = get_database()
        initial_version = ResumeVersion(
            type=resume_in.type,
            latex_code=resume_in.initial_latex,
            status=ResumeStatus.DRAFT,
            updated_at=datetime.now(timezone.utc)
        )
        
        resume_dict = ResumeInDB(
            user_id=user_id,
            versions=[initial_version],
            default_version_id=initial_version.version_id,
            created_at=datetime.now(timezone.utc)
        ).model_dump(by_alias=True)
        
        result = await db.resumes.insert_one(resume_dict)
        inserted_resume = await db.resumes.find_one({"_id": result.inserted_id})
        return ResumeInDB(**inserted_resume)

    @staticmethod
    async def get_student_resumes(user_id: PyObjectId) -> List[ResumeInDB]:
        db = get_database()
        resumes = await db.resumes.find({"user_id": user_id}).to_list(length=100)
        return [ResumeInDB(**r) for r in resumes]

    @staticmethod
    async def get_resume_by_id(resume_id: str) -> Optional[ResumeInDB]:
        db = get_database()
        resume = await db.resumes.find_one({"_id": ObjectId(resume_id)})
        if resume:
            return ResumeInDB(**resume)
        return None

    @staticmethod
    async def add_resume_version(resume_id: str, version_data: ResumeVersion) -> Optional[ResumeInDB]:
        db = get_database()
        await db.resumes.update_one(
            {"_id": ObjectId(resume_id)},
            {"$push": {"versions": version_data.model_dump(by_alias=True)}}
        )
        return await ResumeService.get_resume_by_id(resume_id)

    @staticmethod
    async def update_version_status(
        resume_id: str, 
        version_id: str, 
        status: ResumeStatus
    ) -> bool:
        db = get_database()
        result = await db.resumes.update_one(
            {
                "_id": ObjectId(resume_id),
                "versions.version_id": ObjectId(version_id)
            },
            {
                "$set": {
                    "versions.$.status": status,
                    "versions.$.updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    @staticmethod
    async def update_latest_version(resume_id: str, updates: dict) -> bool:
        db = get_database()
        # Find the resume and update the last version in the array
        result = await db.resumes.update_one(
            {"_id": ObjectId(resume_id)},
            [
                {
                    "$set": {
                        "versions": {
                            "$concatArrays": [
                                {"$slice": ["$versions", {"$subtract": [{"$size": "$versions"}, 1]}]},
                                [
                                    {
                                        "$mergeObjects": [
                                            {"$arrayElemAt": ["$versions", -1]},
                                            {
                                                **updates,
                                                "updated_at": datetime.now(timezone.utc)
                                            }
                                        ]
                                    }
                                ]
                            ]
                        }
                    }
                }
            ]
        )
        return result.modified_count > 0
    @staticmethod
    async def get_validation_queue(
        search: Optional[str] = None,
        year: Optional[int] = None,
        department: Optional[str] = None,
        department_group: Optional[str] = None,
        limit: int = 10
    ) -> List[dict]:
        db = get_database()
        
        pipeline = [
            # 1. Look up user info
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "student"
                }
            },
            {"$unwind": "$student"},
            # 2. Add latest version info for easier filtering
            {
                "$addFields": {
                    "latest_version": {"$arrayElemAt": ["$versions", -1]}
                }
            },
            # 3. Filter for submitted resumes
            {
                "$match": {
                    "latest_version.status": ResumeStatus.SUBMITTED
                }
            }
        ]

        # Apply search
        if search:
            pipeline.append({
                "$match": {
                    "$or": [
                        {"student.name": {"$regex": search, "$options": "i"}},
                        {"student.email": {"$regex": search, "$options": "i"}},
                        {"student.department": {"$regex": search, "$options": "i"}}
                    ]
                }
            })

        # Apply year filter
        if year:
            pipeline.append({
                "$match": {"student.year": year}
            })

        # Apply specific department filter
        if department:
            pipeline.append({
                "$match": {"student.department": {"$regex": f"^{department}$", "$options": "i"}}
            })

        # Apply department group filter (Engineering)
        if department_group == "engineering":
            engg_depts = ["CSE", "ECE", "EE", "ME", "CE", "CHE", "MME", "PIE", "Computer", "Electronics", "Electrical", "Mechanical", "Civil", "Chemical", "Metallurgical", "Production"]
            engg_regex = "|".join(engg_depts)
            pipeline.append({
                "$match": {"student.department": {"$regex": engg_regex, "$options": "i"}}
            })

        # Sort by most recent submission
        pipeline.append({"$sort": {"latest_version.updated_at": -1}})
        
        # Limit to top 10 as per request
        pipeline.append({"$limit": limit})

        # Project output format
        pipeline.append({
            "$project": {
                "_id": 1,
                "studentName": "$student.name",
                "studentEmail": "$student.email",
                "department": "$student.department",
                "year": "$student.year",
                "type": "$latest_version.type",
                "score": "$latest_version.ai_score.total",
                "status": "$latest_version.status",
                "updatedAt": "$latest_version.updated_at"
            }
        })

        results = await db.resumes.aggregate(pipeline).to_list(length=limit)
        # Convert IDs to strings
        for res in results:
            res["id"] = str(res["_id"])
            del res["_id"]
        return results

    @staticmethod
    async def get_students_list(
        search: Optional[str] = None,
        year: Optional[int] = None,
        department: Optional[str] = None,
        limit: int = 50
    ) -> List[dict]:
        db = get_database()
        
        # 1. Pipeline starts with students
        match_query = {"role": UserRole.STUDENT}
        if year:
            match_query["year"] = year
        if department:
            match_query["department"] = {"$regex": f"^{department}$", "$options": "i"}
        if search:
            match_query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"department": {"$regex": search, "$options": "i"}}
            ]

        pipeline = [
            {"$match": match_query},
            # 2. Lookup resumes
            {
                "$lookup": {
                    "from": "resumes",
                    "localField": "_id",
                    "foreignField": "user_id",
                    "as": "resumes"
                }
            },
            # 3. Get the latest resume version
            {
                "$addFields": {
                    "latest_resume": { "$arrayElemAt": ["$resumes", 0] }
                }
            },
            {
                "$addFields": {
                    "latest_version": { "$arrayElemAt": ["$latest_resume.versions", -1] }
                }
            },
            # 4. Limit and Project
            {"$limit": limit},
            {
                "$project": {
                    "_id": 1,
                    "name": 1,
                    "email": 1,
                    "department": 1,
                    "year": 1,
                    "status": { "$ifNull": ["$latest_version.status", "not_created"] },
                    "score": { "$ifNull": ["$latest_version.ai_score.overall", 0] },
                    "updatedAt": { "$ifNull": ["$latest_version.updated_at", "$created_at"] }
                }
            }
        ]

        results = await db.users.aggregate(pipeline).to_list(length=limit)
        
        for res in results:
            res["id"] = str(res["_id"])
            del res["_id"]
        return results
