from textwrap import dedent

from backend.services.extractor_service import ExtractorService


def test_rule_parser_extracts_internship_project_and_awards():
    text = dedent(
        """
    张三
    实习经历
    放疗中心实习生 at 浙江大学医学院附属医院, 杭州 2025-06 - 2026-04
    负责设备使用前准备和患者信息核对。
    教育背景
    本科 - 应用物理学 - 杭州医学院 2022-09 - 2026-06
    获奖荣誉
    优秀实习生 - 实习期间荣誉
    2024-2025学年二等奖学金 - 院校级奖学金 2025-12
    AI新药研发项目 - 院校级二等奖 2025-05
    """
    )

    result, confidence = ExtractorService()._extract_resume_by_rules(text)

    assert confidence > 0.5
    assert len(result["work_experiences"]) == 1
    assert result["work_experiences"][0]["position"] == "放疗中心实习生"
    assert result["work_experiences"][0]["start_date"] == "2025-06"
    assert len(result["project_experiences"]) == 1
    assert result["project_experiences"][0]["name"] == "AI新药研发项目"
    assert len(result["awards"]) == 3
