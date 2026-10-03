from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import DatabaseClient, get_db, get_db_client
from app.services.context import ContextService, get_context_service
from app.services.llm import LLMService, get_llm_service

SettingsDep = Annotated[Settings, Depends(get_settings)]
LLMDep = Annotated[LLMService, Depends(get_llm_service)]
ContextDep = Annotated[ContextService, Depends(get_context_service)]
DBDep = Annotated[Session, Depends(get_db)]
DBClientDep = Annotated[DatabaseClient, Depends(get_db_client)]
