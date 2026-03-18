from typing import List, Optional, Union
from bson import ObjectId
from datetime import datetime, timezone
from fastapi import UploadFile
from app.db.mongodb import get_database
from app.models.resume import ResumeInDB, ResumeVersion, ResumeCreate, ResumeStatus
from app.models.user import PyObjectId, UserRole
from app.services.file_service import FileService

class ResumeService:
    @staticmethod
    async def create_resume(user_id: PyObjectId, resume_in: ResumeCreate, file: Optional[UploadFile] = None) -> ResumeInDB:
        db = get_database()
        
        # 1. Create the resume entry first to get an ID for the directory
        resume_dict = {
            "user_id": user_id,
            "versions": [],
            "created_at": datetime.now(timezone.utc)
        }
        result = await db.resumes.insert_one(resume_dict)
        resume_id = str(result.inserted_id)

        # 2. Handle file upload if present
        file_url = resume_in.file_url
        if file:
            file_url = await FileService.save_resume_file(str(user_id), resume_id, file)

        # 3. Create initial version
        initial_version = ResumeVersion(
            type=resume_in.type,
            format=resume_in.format,
            file_url=file_url,
            latex_code=resume_in.initial_latex or "",
            status=ResumeStatus.DRAFT,
            updated_at=datetime.now(timezone.utc)
        )
        
        # 4. Update the resume with the version
        await db.resumes.update_one(
            {"_id": result.inserted_id},
            {
                "$set": {
                    "versions": [initial_version.model_dump(by_alias=True)],
                    "default_version_id": initial_version.version_id
                }
            }
        )
        
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
    async def add_resume_version(resume_id: str, version_data: ResumeVersion, file: Optional[UploadFile] = None) -> Optional[ResumeInDB]:
        db = get_database()
        resume = await db.resumes.find_one({"_id": ObjectId(resume_id)})
        if not resume:
            return None
            
        # Handle file upload for new version
        if file:
            version_data.file_url = await FileService.save_resume_file(
                str(resume["user_id"]), resume_id, file
            )
            
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
        years: Optional[List[int]] = None,
        departments: Optional[List[str]] = None,
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

        # Apply year filter (Multi-select)
        if years:
            pipeline.append({
                "$match": {"student.year": {"$in": years}}
            })

        # Apply specific department filter (Multi-select)
        if departments:
            pipeline.append({
                "$match": {"student.department": {"$in": departments}}
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
        years: Optional[List[int]] = None,
        departments: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[dict]:
        db = get_database()
        
        # 1. Pipeline starts with students
        match_query = {"role": UserRole.STUDENT}
        if years:
            match_query["year"] = {"$in": years}
        if departments:
            match_query["department"] = {"$in": departments}
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
        return results

    @staticmethod
    async def get_student_dashboard_stats(user_id: PyObjectId) -> dict:
        db = get_database()
        resumes = await db.resumes.find({"user_id": user_id}).to_list(length=100)
        
        active_resumes = len(resumes)
        
        # Calculate Pending Reviews
        pending_reviews = 0
        latest_scores = []
        type_counts = {}
        
        # For history, we'll look at the last 6 months or last 6 versions
        # Mocking activity for now as we don't have a granular "activity log" for daily edits
        activity = [
            {"label": "Mon", "value": 2, "maxValue": 5},
            {"label": "Tue", "value": 3, "maxValue": 5},
            {"label": "Wed", "value": 1, "maxValue": 5},
            {"label": "Thu", "value": 4, "maxValue": 5},
            {"label": "Fri", "value": 2, "maxValue": 5},
            {"label": "Sat", "value": 0, "maxValue": 5},
            {"label": "Sun", "value": 0, "maxValue": 5},
        ]

        for r in resumes:
            if not r.get("versions"):
                continue
                
            latest_version = r["versions"][-1]
            if latest_version.get("status") == ResumeStatus.SUBMITTED:
                pending_reviews += 1
            
            # Type distribution
            res_type = latest_version.get("type", "General")
            type_counts[res_type] = type_counts.get(res_type, 0) + 1
            
            # Average score
            ai_score = latest_version.get("ai_score", {})
            score = ai_score.get("overall") or ai_score.get("total") or 0
            if score > 0:
                latest_scores.append(score)

        avg_score = sum(latest_scores) / len(latest_scores) if latest_scores else 0
        
        # distribution data
        colors = ["var(--primary)", "var(--accent)", "var(--secondary)", "#1e293b", "#64748b"]
        resume_distribution = [
            {"label": k, "value": v, "color": colors[i % len(colors)]}
            for i, (k, v) in enumerate(type_counts.items())
        ]

        # Score history (Simplified: just using the latest from each resume for now)
        # In a real app, this would be a time-series of scores
        score_history = [
            {"label": f"Res {i+1}", "current": s, "previous": max(0, s - 5)}
            for i, s in enumerate(latest_scores[:5])
        ]

        return {
            "stats": [
                {
                    "title": "Active Resumes",
                    "value": active_resumes,
                    "icon": "FileText",
                    "description": f"{len(type_counts)} Categories",
                    "trend": {"value": 0, "isUp": True}
                },
                {
                    "title": "Avg AI Score",
                    "value": f"{round(avg_score)}/100",
                    "icon": "Award",
                    "trend": {"value": 5, "isUp": True}
                },
                {
                    "title": "Pending Reviews",
                    "value": pending_reviews,
                    "icon": "Clock",
                    "description": "Awaiting response"
                },
                {
                    "title": "Placement Goal",
                    "value": "90%", # Hardcoded for now as it's a target
                    "icon": "Target",
                    "description": "Target Readiness",
                    "trend": {"value": 0, "isUp": True}
                }
            ],
            "resumeDistribution": resume_distribution,
            "scoreHistory": score_history,
            "validationActivity": activity
        }

    @staticmethod
    async def get_student_analytics() -> dict:
        db = get_database()
        
        # 1. Get total student count
        total_students = await db.users.count_documents({"role": UserRole.STUDENT})
        
        # 2. Status distribution pipeline
        status_pipeline = [
            {"$match": {"role": UserRole.STUDENT}},
            {
                "$lookup": {
                    "from": "resumes",
                    "localField": "_id",
                    "foreignField": "user_id",
                    "as": "resumes"
                }
            },
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
            {
                "$group": {
                    "_id": { "$ifNull": ["$latest_version.status", "not_created"] },
                    "count": { "$sum": 1 }
                }
            }
        ]
        
        status_data = await db.users.aggregate(status_pipeline).to_list(length=10)
        status_distribution = {item["_id"]: item["count"] for item in status_data}
        
        # 3. Department-wise readiness pipeline
        dept_pipeline = [
            {"$match": {"role": UserRole.STUDENT}},
            {
                "$lookup": {
                    "from": "resumes",
                    "localField": "_id",
                    "foreignField": "user_id",
                    "as": "resumes"
                }
            },
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
            {
                "$addFields": {
                    "is_ready": { "$cond": [{ "$eq": ["$latest_version.status", ResumeStatus.APPROVED] }, 1, 0] }
                }
            },
            {
                "$group": {
                    "_id": "$department",
                    "total": { "$sum": 1 },
                    "ready": { "$sum": "$is_ready" }
                }
            },
            {"$sort": {"ready": -1}}
        ]
        
        dept_data = await db.users.aggregate(dept_pipeline).to_list(length=50)
        
        # 4. Average AI Score (for approved/submitted resumes)
        score_pipeline = [
            {"$unwind": "$versions"},
            {"$match": {"versions.status": {"$in": [ResumeStatus.APPROVED, ResumeStatus.SUBMITTED]}}},
            {
                "$group": {
                    "_id": None,
                    "avg_score": { "$avg": "$versions.ai_score.overall" }
                }
            }
        ]
        score_data = await db.resumes.aggregate(score_pipeline).to_list(length=1)
        avg_score = (score_data[0].get("avg_score") or 0) if score_data else 0

        return {
            "total_students": total_students,
            "status_distribution": status_distribution,
            "department_metrics": [
                {
                    "name": d["_id"],
                    "total": d["total"],
                    "ready": d["ready"],
                    "readiness_rate": round((d["ready"] / d["total"]) * 100, 1) if d["total"] > 0 else 0
                } for d in dept_data
            ],
            "average_score": round(avg_score, 1),
            "overall_readiness": round((status_distribution.get(ResumeStatus.APPROVED, 0) / total_students) * 100, 1) if total_students > 0 else 0
        }

    @staticmethod
    async def get_admin_dashboard_stats() -> dict:
        db = get_database()
        from app.services.audit_service import AuditService
        
        # 1. User Counts by Role
        user_roles_pipeline = [
            {"$group": {"_id": "$role", "count": {"$sum": 1}}}
        ]
        user_role_data = await db.users.aggregate(user_roles_pipeline).to_list(length=10)
        role_map = {item["_id"]: item["count"] for item in user_role_data}
        total_users = sum(role_map.values())
        
        # 2. Total Resumes
        total_resumes = await db.resumes.count_documents({})
        
        # 3. Audit Log Stats
        audit_stats = await AuditService.get_stats()
        
        # 4. User Growth (Mocked for now as we don't have historical snapshots)
        user_growth = [
            {"label": "Week 1", "current": max(0, total_users - 100), "previous": max(0, total_users - 120)},
            {"label": "Week 2", "current": max(0, total_users - 50), "previous": max(0, total_users - 100)},
            {"label": "Week 3", "current": total_users, "previous": max(0, total_users - 50)},
        ]
        
        # Format distribution for DonutChart
        colors = ["var(--primary)", "var(--secondary)", "var(--accent)", "#1e293b"]
        role_names = {
            UserRole.STUDENT: "Students",
            UserRole.FACULTY: "Faculty",
            UserRole.SPC: "SPC",
            UserRole.ADMIN: "Admins"
        }
        role_distribution = [
            {"label": role_names.get(role, role), "value": count, "color": colors[i % len(colors)]}
            for i, (role, count) in enumerate(role_map.items())
        ]

        return {
            "stats": [
                {
                    "title": "Total Users",
                    "value": f"{total_users:,}",
                    "icon": "UserPlus",
                    "trend": {"value": 8, "isUp": True}
                },
                {
                    "title": "Active Resumes",
                    "value": f"{total_resumes:,}",
                    "icon": "Database",
                    "trend": {"value": 12, "isUp": True}
                },
                {
                    "title": "System Health",
                    "value": "99.9%",
                    "icon": "Activity",
                    "description": "All services operational"
                },
                {
                    "title": "Recent Actions",
                    "value": audit_stats.get("total_events", 0),
                    "icon": "History",
                    "description": "Total tracked events"
                }
            ],
            "roleDistribution": role_distribution,
            "userGrowth": user_growth
        }

    @staticmethod
    async def delete_resume(resume_id: str, user_id: PyObjectId) -> bool:
        db = get_database()
        # 1. Get current resume to find user_id for cleanup
        resume = await db.resumes.find_one({"_id": ObjectId(resume_id), "user_id": user_id})
        if not resume:
            return False
            
        # 2. Cleanup physical storage
        import shutil
        import os
        from app.core.config import settings
        
        resume_dir = os.path.join(settings.UPLOAD_DIR, "resumes", str(user_id), str(resume_id))
        if os.path.exists(resume_dir):
            shutil.rmtree(resume_dir)
            
        # 3. Delete from DB
        result = await db.resumes.delete_one({"_id": ObjectId(resume_id)})
        return result.deleted_count > 0
