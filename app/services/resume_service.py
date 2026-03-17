from typing import List, Optional
from bson import ObjectId
from datetime import datetime, timezone
from app.db.mongodb import get_database
from app.models.resume import ResumeInDB, ResumeVersion, ResumeCreate, ResumeStatus
from app.models.user import PyObjectId

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
    async def update_latest_version(resume_id: str, content: str) -> bool:
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
                                                "latex_code": content,
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
