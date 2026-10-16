"""ORM 表结构兼容保护测试。"""

from chiren_backend.platform import db, models


def test_orm_table_names_remain_stable() -> None:
    """确保核心 ORM 表名保持稳定。"""
    assert models.Resume.__tablename__ == "resumes"
    assert models.ResumeSection.__tablename__ == "resume_sections"
    assert models.BaseWork.__tablename__ == "work"
    assert models.ConversationMessageRecord.__tablename__ == "conversation_messages"
    assert models.UserConfig.__tablename__ == "user_config"
    assert models.JobDescriptionProfile.__tablename__ == "job_description_profiles"
    assert models.CoverLetterGenerationBatch.__tablename__ == "cover_letter_generation_batches"
    assert models.JobDescriptionAnalysis.__tablename__ == "job_description_analysis"
    assert models.InterviewCollection.__tablename__ == "interview_collections"
    assert models.InterviewRound.__tablename__ == "interview_rounds"
    assert "template" not in models.Base.metadata.tables


def test_hot_query_indexes_are_declared() -> None:
    """确保常用查询路径有 ORM 索引。"""
    assert {
        "ix_resumes_workspace_created_at",
        "ix_resumes_template",
    } <= _index_names(models.Resume)
    assert {
        "ix_resume_sections_resume_sort",
        "ix_resume_sections_resume_visible_sort",
        "ix_resume_sections_resume_type",
    } <= _index_names(models.ResumeSection)
    assert {
        "ix_work_task_status_updated",
        "ix_work_status_created",
    } <= _index_names(models.BaseWork)
    assert {
        "ix_conversation_messages_conversation_created",
    } <= _index_names(models.ConversationMessageRecord)
    assert {
        "ix_jd_profiles_resume_hash",
        "ix_jd_profiles_resume_status",
        "ix_jd_profiles_status_updated",
    } <= _index_names(models.JobDescriptionProfile)
    assert {
        "ix_cover_letters_resume_created",
        "ix_cover_letters_resume_status",
        "ix_cover_letters_source_hash",
    } <= _index_names(models.CoverLetterGenerationBatch)
    assert {
        "ix_jd_analysis_resume_created",
    } <= _index_names(models.JobDescriptionAnalysis)
    assert {
        "ix_interview_collections_resume_created",
        "ix_interview_collections_status",
    } <= _index_names(models.InterviewCollection)
    assert {
        "ix_interview_rounds_collection_sort",
        "ix_interview_rounds_collection_status",
    } <= _index_names(models.InterviewRound)


def test_sqlite_expression_indexes_are_configured() -> None:
    """确保启动时会创建 JSON 元数据索引。"""
    joined = "\n".join(db.SQLITE_INDEXES)
    assert "ix_work_task_status_meta_resume_id" in joined
    assert "ix_work_task_status_meta_round_id" in joined
    assert "ix_work_task_status_meta_collection_id" in joined
    assert "ix_work_task_status_meta_source_hash" in joined
    assert "json_extract(meta_info, '$.resume_id')" in joined
    assert "json_extract(meta_info, '$.round_id')" in joined
    assert "json_extract(meta_info, '$.collection_id')" in joined
    assert "json_extract(meta_info, '$.source_hash')" in joined


def _index_names(model: type[models.Base]) -> set[str]:
    """读取模型声明的索引名。"""
    return {index.name for index in model.__table__.indexes}
