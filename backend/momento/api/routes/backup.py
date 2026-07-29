"""Backup and restore API endpoints for comprehensive project backup."""

from __future__ import annotations

import datetime
import json
import os
import shutil
import sqlite3
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from ... import config, db
from ..deps import optional_user

router = APIRouter(prefix="/admin/backup", tags=["backup-admin"])


class BackupRequest(BaseModel):
    """Backup request model."""
    include_source: bool = True
    include_database: bool = True
    include_config: bool = True
    include_memory: bool = True
    include_logs: bool = False
    description: Optional[str] = None


class BackupStatus(BaseModel):
    """Backup status model."""
    backup_id: str
    status: str
    created_at: str
    description: Optional[str]
    components: Dict[str, Any]
    file_path: Optional[str]
    file_size: Optional[int]


class RestoreRequest(BaseModel):
    """Restore request model."""
    backup_id: str
    components: List[str]  # Which components to restore


def get_backup_dir() -> Path:
    """Get or create backup directory."""
    backup_dir = Path(__file__).resolve().parent.parent.parent.parent / "backups" / "snapshots"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def generate_backup_id() -> str:
    """Generate unique backup ID based on timestamp."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")


def backup_database(backup_path: Path) -> Dict[str, Any]:
    """Backup SQLite database."""
    try:
        db_path = Path(config.DATABASE_PATH)
        if not db_path.exists():
            return {"status": "skipped", "reason": "Database file not found"}
        
        # Copy database file
        backup_db_path = backup_path / "database"
        backup_db_path.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_path, backup_db_path / "momento.db")
        
        # Get database stats
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        tables = {}
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for (table_name,) in cursor.fetchall():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            tables[table_name] = count
        
        conn.close()
        
        return {
            "status": "success",
            "tables": tables,
            "file_size": db_path.stat().st_size
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def backup_source_code(backup_path: Path) -> Dict[str, Any]:
    """Backup project source code."""
    try:
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        backup_src_path = backup_path / "source"
        backup_src_path.mkdir(parents=True, exist_ok=True)
        
        # Create a compressed archive of source code
        source_files = []
        excluded_dirs = {
            "node_modules", "__pycache__", ".git", "dist", "build", 
            ".next", "coverage", ".pytest_cache", "venv", "env", ".venv"
        }
        
        # Copy Python backend
        backend_dir = root_dir / "backend"
        if backend_dir.exists():
            backup_backend = backup_src_path / "backend"
            shutil.copytree(backend_dir, backup_backend, 
                          ignore=shutil.ignore_patterns(*["__pycache__", "*.pyc", ".pytest_cache"]))
            source_files.append("backend")
        
        # Copy web frontend
        web_dir = root_dir / "web"
        if web_dir.exists():
            backup_web = backup_src_path / "web"
            shutil.copytree(web_dir, backup_web,
                          ignore=shutil.ignore_patterns(*["node_modules", "dist", ".next"]))
            source_files.append("web")
        
        # Copy infrastructure
        infra_dir = root_dir / "infrastructure"
        if infra_dir.exists():
            backup_infra = backup_src_path / "infrastructure"
            shutil.copytree(infra_dir, backup_infra)
            source_files.append("infrastructure")
        
        return {
            "status": "success",
            "components": source_files,
            "excluded_dirs": list(excluded_dirs)
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def backup_config(backup_path: Path) -> Dict[str, Any]:
    """Backup configuration files."""
    try:
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        backup_config_path = backup_path / "config"
        backup_config_path.mkdir(parents=True, exist_ok=True)
        
        config_files = []
        
        # Copy .devin directory
        devin_dir = root_dir / ".devin"
        if devin_dir.exists():
            backup_devin = backup_config_path / ".devin"
            shutil.copytree(devin_dir, backup_devin)
            config_files.append(".devin")
        
        # Copy .agents directory
        agents_dir = root_dir / ".agents"
        if agents_dir.exists():
            backup_agents = backup_config_path / ".agents"
            shutil.copytree(agents_dir, backup_agents)
            config_files.append(".agents")
        
        # Copy environment files
        env_files = [".env", ".env.example", "package.json", "requirements.txt"]
        for env_file in env_files:
            env_path = root_dir / env_file
            if env_path.exists():
                shutil.copy2(env_path, backup_config_path / env_file)
                config_files.append(env_file)
        
        return {
            "status": "success",
            "files": config_files
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def backup_memory(backup_path: Path) -> Dict[str, Any]:
    """Backup AI memory and project memory."""
    try:
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        backup_memory_path = backup_path / "memory"
        backup_memory_path.mkdir(parents=True, exist_ok=True)
        
        memory_files = []
        
        # Copy .devin/memory
        devin_memory = root_dir / ".devin" / "memory"
        if devin_memory.exists():
            backup_devin_memory = backup_memory_path / "devin_memory"
            shutil.copytree(devin_memory, backup_devin_memory)
            memory_files.append("devin_memory")
        
        # Copy global memory
        global_memory = Path.home() / ".config" / "devin"
        if global_memory.exists():
            backup_global_memory = backup_memory_path / "global_memory"
            shutil.copytree(global_memory, backup_global_memory)
            memory_files.append("global_memory")
        
        # Copy project memory files
        memory_patterns = ["*memory*.json", "*memory*.md", "AGENTS.md", "CODING_STANDARDS.md"]
        for pattern in memory_patterns:
            for memory_file in root_dir.glob(pattern):
                if memory_file.is_file():
                    shutil.copy2(memory_file, backup_memory_path / memory_file.name)
                    memory_files.append(memory_file.name)
        
        return {
            "status": "success",
            "files": memory_files
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def backup_logs(backup_path: Path) -> Dict[str, Any]:
    """Backup log files."""
    try:
        log_dir = Path(config.LOG_DIR)
        if not log_dir.exists():
            return {"status": "skipped", "reason": "Log directory not found"}
        
        backup_logs_path = backup_path / "logs"
        backup_logs_path.mkdir(parents=True, exist_ok=True)
        
        # Copy log files
        log_files = []
        for log_file in log_dir.glob("*.log"):
            shutil.copy2(log_file, backup_logs_path / log_file.name)
            log_files.append(log_file.name)
        
        return {
            "status": "success",
            "files": log_files
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@router.post("/create")
async def create_backup(
    request: BackupRequest,
    user: Dict[str, Any] = Depends(optional_user)
) -> BackupStatus:
    """Create a comprehensive backup of the project."""
    backup_id = generate_backup_id()
    backup_dir = get_backup_dir()
    temp_backup_dir = backup_dir / f"temp_{backup_id}"
    
    try:
        temp_backup_dir.mkdir(parents=True, exist_ok=True)
        
        components = {}
        
        # Backup database
        if request.include_database:
            components["database"] = backup_database(temp_backup_dir)
        
        # Backup source code
        if request.include_source:
            components["source"] = backup_source_code(temp_backup_dir)
        
        # Backup configuration
        if request.include_config:
            components["config"] = backup_config(temp_backup_dir)
        
        # Backup memory
        if request.include_memory:
            components["memory"] = backup_memory(temp_backup_dir)
        
        # Backup logs
        if request.include_logs:
            components["logs"] = backup_logs(temp_backup_dir)
        
        # Create backup metadata
        metadata = {
            "backup_id": backup_id,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "created_by": user.get("email", "system") if user else "system",
            "description": request.description,
            "components": components,
            "version": "1.0"
        }
        
        with open(temp_backup_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Create compressed archive
        archive_path = backup_dir / f"backup_{backup_id}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(temp_backup_dir, arcname=f"backup_{backup_id}")
        
        # Clean up temp directory
        shutil.rmtree(temp_backup_dir)
        
        # Log audit
        if user:
            db.log_audit(user["email"], "backup_created", {
                "backup_id": backup_id,
                "components": list(components.keys()),
                "description": request.description
            })
        
        return BackupStatus(
            backup_id=backup_id,
            status="completed",
            created_at=metadata["created_at"],
            description=request.description,
            components=components,
            file_path=str(archive_path),
            file_size=archive_path.stat().st_size
        )
        
    except Exception as e:
        # Clean up on failure
        if temp_backup_dir.exists():
            shutil.rmtree(temp_backup_dir)
        
        if user:
            db.log_audit(user["email"], "backup_failed", {
                "backup_id": backup_id,
                "error": str(e)
            })
        
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@router.get("/list")
async def list_backups(user: Dict[str, Any] = Depends(optional_user)) -> Dict[str, Any]:
    """List all available backups."""
    backup_dir = get_backup_dir()
    
    backups = []
    for backup_file in backup_dir.glob("backup_*.tar.gz"):
        try:
            # Extract metadata from archive
            with tarfile.open(backup_file, "r:gz") as tar:
                metadata_file = None
                for member in tar.getmembers():
                    if member.name.endswith("metadata.json"):
                        metadata_file = member
                        break
                
                if metadata_file:
                    f = tar.extractfile(metadata_file)
                    metadata = json.load(f)
                    backups.append({
                        "backup_id": metadata.get("backup_id"),
                        "created_at": metadata.get("created_at"),
                        "created_by": metadata.get("created_by"),
                        "description": metadata.get("description"),
                        "components": list(metadata.get("components", {}).keys()),
                        "file_size": backup_file.stat().st_size,
                        "file_path": str(backup_file)
                    })
        except Exception as e:
            # Skip corrupted backups
            continue
    
    # Sort by creation date (newest first)
    backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "backups": backups,
        "total_count": len(backups),
        "backup_directory": str(backup_dir)
    }


@router.get("/status/{backup_id}")
async def get_backup_status(
    backup_id: str,
    user: Dict[str, Any] = Depends(optional_user)
) -> Dict[str, Any]:
    """Get detailed status of a specific backup."""
    backup_dir = get_backup_dir()
    backup_file = backup_dir / f"backup_{backup_id}.tar.gz"
    
    if not backup_file.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    
    try:
        with tarfile.open(backup_file, "r:gz") as tar:
            metadata_file = None
            for member in tar.getmembers():
                if member.name.endswith("metadata.json"):
                    metadata_file = member
                    break
            
            if metadata_file:
                f = tar.extractfile(metadata_file)
                metadata = json.load(f)
                return {
                    "backup_id": backup_id,
                    "metadata": metadata,
                    "file_size": backup_file.stat().st_size,
                    "file_path": str(backup_file),
                    "exists": True
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read backup metadata: {str(e)}")


@router.delete("/delete/{backup_id}")
async def delete_backup(
    backup_id: str,
    user: Dict[str, Any] = Depends(optional_user)
) -> Dict[str, Any]:
    """Delete a specific backup."""
    backup_dir = get_backup_dir()
    backup_file = backup_dir / f"backup_{backup_id}.tar.gz"
    
    if not backup_file.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    
    try:
        backup_file.unlink()
        
        # Log audit
        if user:
            db.log_audit(user["email"], "backup_deleted", {
                "backup_id": backup_id
            })
        
        return {
            "status": "deleted",
            "backup_id": backup_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")


@router.post("/restore/{backup_id}")
async def restore_backup(
    backup_id: str,
    request: RestoreRequest,
    user: Dict[str, Any] = Depends(optional_user)
) -> Dict[str, Any]:
    """Restore from a specific backup."""
    backup_dir = get_backup_dir()
    backup_file = backup_dir / f"backup_{backup_id}.tar.gz"
    
    if not backup_file.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    
    try:
        temp_restore_dir = backup_dir / f"temp_restore_{backup_id}"
        temp_restore_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract backup
        with tarfile.open(backup_file, "r:gz") as tar:
            tar.extractall(temp_restore_dir)
        
        # Read metadata
        metadata_file = temp_restore_dir / f"backup_{backup_id}" / "metadata.json"
        with open(metadata_file) as f:
            metadata = json.load(f)
        
        restore_results = {}
        
        # Restore components based on request
        if "database" in request.components and "database" in metadata["components"]:
            # Database restore logic here
            restore_results["database"] = {"status": "not_implemented"}
        
        if "source" in request.components and "source" in metadata["components"]:
            # Source restore logic here
            restore_results["source"] = {"status": "not_implemented"}
        
        if "config" in request.components and "config" in metadata["components"]:
            # Config restore logic here
            restore_results["config"] = {"status": "not_implemented"}
        
        if "memory" in request.components and "memory" in metadata["components"]:
            # Memory restore logic here
            restore_results["memory"] = {"status": "not_implemented"}
        
        # Clean up
        shutil.rmtree(temp_restore_dir)
        
        # Log audit
        if user:
            db.log_audit(user["email"], "backup_restore", {
                "backup_id": backup_id,
                "components": request.components,
                "results": restore_results
            })
        
        return {
            "status": "completed",
            "backup_id": backup_id,
            "restored_components": restore_results
        }
        
    except Exception as e:
        # Clean up on failure
        if temp_restore_dir.exists():
            shutil.rmtree(temp_restore_dir)
        
        if user:
            db.log_audit(user["email"], "backup_restore_failed", {
                "backup_id": backup_id,
                "error": str(e)
            })
        
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")