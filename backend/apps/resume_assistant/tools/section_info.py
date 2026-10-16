from typing import Literal

from pydantic import BaseModel, Field

from shared.types.base_tool import BaseTool, ToolExecutionContext, ToolResult

# 各区块类型的详细定义说明（供 LLM 理解结构使用）
_SECTION_DEFINITIONS: dict[str, str] = {
    "personal_info": """
Personal Information Section

Contains the card owner's basic identifying information.

Fields:
- full_name (string): Full legal name, e.g., "Zhang Zhenxiang"
- job_title (string): Target position/intended role, e.g., "AI Agent Developer / Python Developer"
- email (string): Contact email address, e.g., "401303740@qq.com"
- phone (string): Contact phone number, e.g., "19720136938"
- location (string): Current city of residence, e.g., "Shenzhen"
- salary (string): Expected salary range, e.g., "4-6K"
- age (string): Age, e.g., "21"
- gender (string): Gender, e.g., "Male"
- political_status (string): Political affiliation, e.g., "Communist Party Member"
- education_level (string): Highest education level, e.g., "Bachelor's"
- ethnicity (string): Ethnicity, e.g., "Han"
- hometown (string): Hometown, e.g., "Hunan"
- marital_status (string): Marital status, e.g., "Single"
- years_of_experience (string): Years of work experience, e.g., "3"
- wechat (string): WeChat ID, e.g., "zhangsan"
- website (string): Personal website, e.g., "https://example.com"
- linkedin (string): LinkedIn profile, e.g., "https://linkedin.com/in/xxx"
""",
    "summary": """
Personal Summary Section

A narrative paragraph introducing the card owner.

Fields:
- text (text): Free-form introduction text, e.g., "Currently pursuing a Bachelor's degree in Artificial Intelligence..." """,
    "work_experience": """Work Experience Section

List of past employment and professional positions.

Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier, e.g., "a1b2c3d4-0001"
- company (string): Organization name, e.g., "Hunan University of Technology Innovation Center"
- position (string): Job title/role, e.g., "AI Native Application Development Team Member"
- location (string): Work location, e.g., "Zhuzhou"
- start_date (string): Start date in YYYY-MM or YYYY format, e.g., "2023-09"
- end_date (string): End date or "Present", e.g., "Present"
- current (boolean): Whether this is the current job, e.g., true
- description (text): Detailed job description
- technologies (array[string]): Tech stack, e.g., ["Python", "FastAPI"]
- highlights (array[string]): Key achievements or highlights, e.g., ["Led model API封装...", ...]""",
    "education": """
Education Background Section

List of educational history entries.

Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier, e.g., "e1f2g3h4-0001"
- institution (string): School/university name, e.g., "Hunan University of Technology"
- degree (string): Degree earned, e.g., "Bachelor's"
- field (string): Major/field of study, e.g., "Artificial Intelligence"
- location (string): Geographic location, e.g., "Hunan·Zhuzhou"
- start_date (string): Enrollment date, e.g., "2023-09"
- end_date (string): Expected graduation date, e.g., "2027"
- gpa (string): Grade point average, e.g., "3.8/4.0"
- highlights (array[string]): Honors/achievements, e.g., ["湖南省大学生程序设计竞赛二等奖", ...]""",
    "skills": """
Skills Section

Skills organized by category.

Structure: Contains a "categories" array.
Each category:
- id (string): Unique identifier, e.g., "s1t2u3v4-0001"
- name (string): Category name, e.g., "LLM & Agent (Core)"
- skills (array[string]): List of skills in this category, e.g., ["LangChain", "LangGraph", "RAG"]""",
    "languages": """
Language Proficiency Section

List of languages the person can use.

Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier, e.g., "a1b5c3d4-0001"
- language (string): Language name, e.g., "English"
- proficiency (string): Proficiency level, e.g., "CET-6"
- description (string): Additional notes, e.g., "Good command of all skills" """,
    "projects": """Project Experience Section

List of independent projects or portfolio items.

Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier, e.g., "ccb2c3d4-0001"
- name (string): Project name, e.g., "AI Resume Generator"
- description (text): Detailed project description, e.g., "Application for AI-auto generating and improving resumes"
- technologies (array[string]): Tech stack, e.g., ["React", "FastAPI", "OpenAI", "ToolCall"]
- highlights (array[string]): Key features/achievements, e.g., ["Multiple AI-auto generation features"]
- url (string): Project link, e.g., "https://github.com/..."
- start_date (string): Start date, e.g., "2026-04"
- end_date (string): End date, e.g., "2026-05" """,
    "certifications": """Certifications Section

List of professional certifications and qualifications.

Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier, e.g., "d1b2c3d4-0001"
- name (string): Certification name, e.g., "CET-4"
- issuer (string): Issuing organization, e.g., "National Education Committee"
- date (string): Date obtained, e.g., "2022年"
- description (string): Certification description """,
    "github": """
GitHub Projects Section

Showcase of GitHub repositories.

Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier, e.g., "51b2c3d4-0001"
- repo_url (string): GitHub repository URL, e.g., "https://github.com/zhangzhenxiang6666"
- name (string): Repository name
- stars (int): Number of stars received
- language (string): Primary programming language
- description (text): Repository description""",
    "qr_codes": """
QR Codes Section

Collection of QR code links.

Structure: Contains an "items" array (may be empty).
Each item:
- id (string): Unique identifier
- url (string): URL the QR code points to
- label (string): Display label for the QR code""",
    "custom": """
Custom Section

User-defined section for miscellaneous content like competitions.

Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier, e.g., "71b2c3d4-0001"
- title (string): Item title, e.g., "XX Competition"
- description (text): Item description with line break support, e.g., "XX competition description\\nDetails here"
- date (string): Date range, e.g., "2024年01月01日-2024年01月03日" """,
}


class SectionInfoToolInput(BaseModel):
    type: Literal[
        "personal_info",
        "summary",
        "work_experience",
        "projects",
        "education",
        "skills",
        "languages",
        "certifications",
        "qr_codes",
        "github",
        "custom",
    ] = Field(description="Section type to retrieve definition for")


class SectionInfoTool(BaseTool):
    name = "section_info"
    description = "Get detailed definition of section content by section type"
    input_model = SectionInfoToolInput

    async def execute(
        self, arguments: SectionInfoToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        return ToolResult(
            output=_SECTION_DEFINITIONS.get(
                arguments.type, f"Unknown section type: {arguments.type}"
            )
        )
