from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.llm_service import LLMService
from app.api.searches import router as searches_router
from app.config import get_settings
from app.graph.workflow import build_graph
from app.services.candidate_repository import CandidateRepository


@dataclass
class Dependencies:
    repository: CandidateRepository
    graph: object


def create_app() -> FastAPI:
    settings = get_settings()
    repository = CandidateRepository(settings.dataset_path)
    llm_service = LLMService(settings)
    graph = build_graph(llm_service)

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.dependencies = Dependencies(repository=repository, graph=graph)
    app.include_router(searches_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
