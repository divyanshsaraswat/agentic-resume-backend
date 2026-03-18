import os
import shutil
from fastapi import UploadFile, HTTPException
from app.core.config import settings
from app.db.mongodb import get_database
from bson import ObjectId

class FileService:
    @staticmethod
    def get_user_dir(user_id: str) -> str:
        # Standard structure: public/resumes/{user_id}
        return os.path.join(settings.UPLOAD_DIR, "resumes", str(user_id))

    @staticmethod
    def get_resume_dir(user_id: str, resume_id: str) -> str:
        # Standard structure: public/resumes/{user_id}/{resume_id}
        return os.path.join(FileService.get_user_dir(user_id), str(resume_id))

    @staticmethod
    async def save_resume_file(user_id: str, resume_id: str, file: UploadFile) -> str:
        """
        Saves a resume file and returns the relative URL path.
        Enforces user storage quotas before saving.
        """
        db = get_database()
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 1. Read file content to get size
        content = await file.read()
        file_size = len(content)
        await file.seek(0) # Reset pointer for saving

        # 2. Check quota
        current_usage = FileService.get_storage_usage(user_id)
        limit_bytes = user.get("storage_limit_mb", 20) * 1024 * 1024
        
        if current_usage + file_size > limit_bytes:
            raise HTTPException(
                status_code=413, 
                detail=f"Storage quota exceeded. Limit: {user.get('storage_limit_mb', 20)}MB"
            )

        # 3. Create directory
        resume_dir = FileService.get_resume_dir(user_id, resume_id)
        if not os.path.exists(resume_dir):
            os.makedirs(resume_dir)
        
        # 4. Save file
        file_path = os.path.join(resume_dir, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # 5. Update user storage tracking in DB
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"storage_used_bytes": current_usage + file_size}}
        )
        
        # Return relative path for static file serving URL
        # e.g., /public/resumes/USER_ID/RESUME_ID/FILENAME.pdf
        return f"/{settings.UPLOAD_DIR}/resumes/{user_id}/{resume_id}/{file.filename}"

    @staticmethod
    def delete_resume_file(relative_path: str):
        """
        Removes a file from the localized storage.
        """
        if not relative_path:
            return
            
        # relative_path looks like /public/resumes/...
        # Remove leading slash if it exists to make it a local path
        path = relative_path.lstrip('/')
        if os.path.exists(path):
            os.remove(path)
            # Note: We don't update DB immediately here as usage is calculated dynamically
            # or updated on the next upload.

    @staticmethod
    def get_storage_usage(user_id: str) -> int:
        """
        Calculates the total size of files stored for a user in bytes.
        """
        user_dir = FileService.get_user_dir(user_id)
        total_size = 0
        if os.path.exists(user_dir):
            for dirpath, dirnames, filenames in os.walk(user_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    # Skip symlinks
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        return total_size
