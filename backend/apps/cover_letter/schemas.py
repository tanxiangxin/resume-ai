from shared.types.cover_letter import CoverLetterGenerationParams


class CoverLetterRequest(CoverLetterGenerationParams):
    resume_id: str
