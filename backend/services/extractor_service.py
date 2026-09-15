"""
智能提取服务 - 支持规则提取和大模型提取
采用混合策略：规则优先，大模型兜底
"""
import re
import hashlib
import jieba.analyse
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import json
import asyncio
import concurrent.futures
import unicodedata

from backend.services.openai_service import OpenAIService
from backend.utils.logger import logger


class ExtractorService:
    """智能提取服务"""
    
    def __init__(self):
        self.openai_service = OpenAIService()
        
        # 技能词库（可扩展）
        self.tech_keywords = {
            # 编程语言
            'languages': [
                'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'Golang', 'C++', 'C#',
                'Ruby', 'PHP', 'Swift', 'Kotlin', 'Rust', 'Scala', 'R', 'Matlab',
                'Shell', 'Bash', 'SQL', 'HTML', 'CSS'
            ],
            # 后端框架
            'backend_frameworks': [
                'Django', 'FastAPI', 'Flask', 'Spring', 'SpringBoot', 'Express',
                'Node.js', 'Koa', 'Gin', 'Beego', 'Rails', 'Laravel', 'ASP.NET'
            ],
            # 前端框架
            'frontend_frameworks': [
                'React', 'Vue', 'Angular', 'Next.js', 'Nuxt.js', 'jQuery',
                'Bootstrap', 'Tailwind', 'Ant Design', 'Element UI', 'uni-app', '微信小程序'
            ],
            # 数据库
            'databases': [
                'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server',
                'Elasticsearch', 'Cassandra', 'HBase', 'ClickHouse', 'TiDB'
            ],
            # 中间件/工具
            'middleware': [
                'Kafka', 'RabbitMQ', 'RocketMQ', 'Nginx', 'Docker', 'Kubernetes',
                'K8s', 'Jenkins', 'Git', 'SVN', 'Maven', 'Gradle'
            ],
            # 云服务
            'cloud': [
                'AWS', 'Azure', 'GCP', '阿里云', '腾讯云', '华为云'
            ],
            # 大数据/AI
            'data_ai': [
                'Hadoop', 'Spark', 'Flink', 'TensorFlow', 'PyTorch', 'Keras',
                'Scikit-learn', 'Pandas', 'NumPy', 'OpenCV'
            ]
        }
        
        # 扁平化技能列表
        self.all_skills = []
        for category in self.tech_keywords.values():
            self.all_skills.extend(category)
        
        # 公司词库（TOP 100，可扩展）
        self.companies = [
            '腾讯', '阿里巴巴', '阿里', '字节跳动', '百度', '美团', '京东', '网易',
            '滴滴', '小米', '华为', 'OPPO', 'VIVO', '拼多多', '快手', '哔哩哔哩',
            'B站', '蚂蚁集团', '蚂蚁金服', '顺丰', '携程', '同程', '去哪儿',
            '新浪', '搜狐', '360', '小红书', '知乎', '微博', 'CSDN'
        ]
        
        # 大学词库（211/985 + 知名院校）
        self.universities = [
            '清华大学', '北京大学', '复旦大学', '上海交通大学', '浙江大学',
            '南京大学', '中国科学技术大学', '中科大', '哈尔滨工业大学', '哈工大',
            '西安交通大学', '华中科技大学', '武汉大学', '同济大学', '北京航空航天大学',
            '北航', '天津大学', '南开大学', '东南大学', '中山大学', '厦门大学',
            '北京理工大学', '北理工', '电子科技大学', '西北工业大学', '中南大学'
        ]
    
    def calculate_content_hash(self, text: str) -> str:
        """计算文本哈希（用于缓存）"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    @staticmethod
    def _extract_section(
        text: str,
        start_markers: List[str],
        end_markers: List[str],
    ) -> str:
        """按独立标题提取章节，避免把相邻章节内容混在一起。"""
        starts = "|".join(re.escape(marker) for marker in start_markers)
        ends = "|".join(re.escape(marker) for marker in end_markers)
        match = re.search(
            rf"^[ \t]*(?:{starts})[ \t]*(?:[：:]|(?=\r?$))(?P<body>.*?)(?=^[ \t]*(?:{ends})[ \t]*(?:[：:]|(?=\r?$))|\Z)",
            text,
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        return match.group("body").strip() if match else ""

    @staticmethod
    def _section_lines(section: str) -> List[str]:
        """清理章节文本中的空行，保留 PDF 提取出的行结构。"""
        return [line.strip() for line in section.splitlines() if line.strip()]
    
    def extract_resume(
        self, 
        text: str, 
        use_llm: bool = False,
        force_llm: bool = False
    ) -> Tuple[Dict[str, Any], float, str]:
        """
        提取简历结构化数据
        
        Args:
            text: 简历文本
            use_llm: 是否允许使用大模型
            force_llm: 是否强制使用大模型（跳过规则提取）
        
        Returns:
            (structured_data, confidence, method)
        """
        text = unicodedata.normalize("NFKC", text)
        logger.info(f"开始提取简历，长度: {len(text)}，use_llm={use_llm}, force_llm={force_llm}")
        
        # 用户选择 AI 或接口要求强制 AI 时，始终走大模型路径。
        if use_llm:
            return self._extract_resume_by_llm(text)
        
        # 先尝试规则提取
        structured_data, confidence = self._extract_resume_by_rules(text)
        
        # 置信度足够，直接返回
        if confidence >= 0.7:
            logger.info(f"规则提取成功，置信度: {confidence}")
            return structured_data, confidence, 'rule'
        
        # 置信度低，且允许使用大模型
        if use_llm and confidence < 0.7:
            logger.warning(f"规则提取置信度低 ({confidence})，调用大模型")
            return self._extract_resume_by_llm(text)
        
        # 不允许使用大模型，返回规则结果
        logger.info(f"规则提取完成，置信度: {confidence}")
        return structured_data, confidence, 'rule'
    
    def _extract_resume_by_rules(self, text: str) -> Tuple[Dict[str, Any], float]:
        """规则提取简历"""
        result = {}
        confidence_scores = []
        
        # 1. 提取基本信息
        # 姓名（简单规则：第一行或"姓名："后）
        name_patterns = [
            r'姓\s*名[：:]\s*([^\n]{2,10})',
            r'^([^\n]{2,4})\n',  # 第一行2-4个字
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                result['name'] = match.group(1).strip()
                confidence_scores.append(1.0)
                break
        else:
            confidence_scores.append(0.0)
        
        # 电话
        phone_match = re.search(r'1[3-9]\d{9}', text)
        if phone_match:
            result['phone'] = phone_match.group(0)
            confidence_scores.append(1.0)
        else:
            confidence_scores.append(0.0)
        
        # 邮箱
        email_match = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', text)
        if email_match:
            result['email'] = email_match.group(0)
            confidence_scores.append(1.0)
        else:
            confidence_scores.append(0.0)
        
        # 年龄
        age_patterns = [
            r'(\d{1,2})\s*岁',
            r'年龄[：:]\s*(\d{1,2})',
        ]
        for pattern in age_patterns:
            match = re.search(pattern, text)
            if match:
                age = int(match.group(1))
                if 18 <= age <= 65:
                    result['age'] = age
                    confidence_scores.append(1.0)
                    break
        else:
            confidence_scores.append(0.5)  # 年龄非必需
        
        # 性别
        if '男' in text and '女' not in text:
            result['gender'] = '男'
            confidence_scores.append(1.0)
        elif '女' in text and '男' not in text:
            result['gender'] = '女'
            confidence_scores.append(1.0)
        else:
            confidence_scores.append(0.5)
        
        # 工作年限
        experience_patterns = [
            r'(\d+)\s*[年\+]\s*(?:以上)?(?:工作)?经验',
            r'(?:超过|拥有|具有)\s*(\d+)\s*年',
            r'(\d+)\+?\s*years?',
        ]
        for pattern in experience_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['years_experience'] = int(match.group(1))
                confidence_scores.append(1.0)
                break
        else:
            confidence_scores.append(0.3)
        
        # 2. 提取教育背景
        # 学历
        education_keywords = ['博士', '硕士', '研究生', '本科', '学士', '专科', '大专']
        for edu in education_keywords:
            if edu in text:
                result['education'] = edu
                confidence_scores.append(1.0)
                break
        else:
            confidence_scores.append(0.0)
        
        # 大学
        for university in self.universities:
            if university in text:
                result['university'] = university
                confidence_scores.append(1.0)
                break
        else:
            # 尝试正则
            uni_match = re.search(r'([^\s]{2,10}(?:大学|学院|理工))', text)
            if uni_match:
                result['university'] = uni_match.group(1)
                confidence_scores.append(0.7)
            else:
                confidence_scores.append(0.0)
        
        # 专业
        major_match = re.search(r'(?:专业[：:]|主修)\s*([^\n]{2,20})', text)
        if major_match:
            result['major'] = major_match.group(1).strip()
            confidence_scores.append(0.8)
        else:
            confidence_scores.append(0.5)
        
        # 3. 提取技能
        skills = []
        for skill in self.all_skills:
            if skill in text or skill.lower() in text.lower():
                skills.append(skill)
        
        # 去重并排序
        skills = list(set(skills))
        if skills:
            result['skills'] = skills
            confidence_scores.append(min(len(skills) / 10, 1.0))  # 最多10个技能满分
        else:
            # 用 jieba 提取关键词
            keywords = jieba.analyse.extract_tags(text, topK=15, withWeight=False)
            result['skills'] = keywords[:10]
            confidence_scores.append(0.5)
        
        # 4. 提取工作/实习经历
        section_headers = [
            '工作经历', '工作经验', '工作履历', '职业经历', '任职经历',
            '实习经历', '实习经验', '项目经历', '项目经验', '项目履历',
            '主要项目', '教育背景', '教育经历', '学历', '技能', '技能特长',
            '技能特⻓', '专业技能', '技术栈', '自我评价', '个人简介',
            '获奖荣誉', '获奖经历', '奖项', '荣誉', '奖学金', '证书',
            '资格证书', '专业证书',
        ]
        work_section = self._extract_section(
            text,
            ['工作经历', '工作经验', '工作履历', '职业经历', '任职经历', '实习经历', '实习经验'],
            section_headers,
        )
        work_lines = self._section_lines(work_section)
        date_range_pattern = re.compile(
            r'(?P<start>\d{4}(?:[.\-/]\d{1,2}|年\d{1,2}月?))\s*'
            r'(?:-|—|–|－|至|到)\s*'
            r'(?P<end>\d{4}(?:[.\-/]\d{1,2}|年\d{1,2}月?)|至今|现在)'
        )
        experience_headers = [
            (index, date_range_pattern.search(line))
            for index, line in enumerate(work_lines)
        ]
        experience_headers = [item for item in experience_headers if item[1]]
        experiences = []

        for header_index, date_match in experience_headers:
            line = work_lines[header_index]
            before_date = line[:date_match.start()].strip(' ,，')
            after_date = line[date_match.end():].strip(' ,，')
            header = before_date or after_date
            position = header
            company = None

            at_parts = re.split(r'\s+(?:at|@)\s+', header, maxsplit=1, flags=re.IGNORECASE)
            if len(at_parts) == 2:
                position = at_parts[0].strip()
                company = re.split(r'\s*[,，]\s*', at_parts[1], maxsplit=1)[0].strip()
            else:
                for known_company in self.companies:
                    if known_company in header:
                        company = known_company
                        position = header.replace(known_company, '').strip(' ,，-')
                        break

            next_header_index = len(work_lines)
            for candidate_index, _ in experience_headers:
                if candidate_index > header_index:
                    next_header_index = candidate_index
                    break
            description_lines = work_lines[header_index + 1:next_header_index]
            achievements = [
                line for line in description_lines
                if re.search(r'获评|获得|锦旗|优秀|提升|成果|完成', line)
            ]
            experience = {
                'period': date_match.group(0).strip(),
                'start_date': date_match.group('start'),
                'end_date': date_match.group('end'),
                'company': company,
                'position': position,
                'description': ' '.join(description_lines),
                'responsibilities': description_lines,
            }
            if achievements:
                experience['achievements'] = achievements
            experiences.append(experience)

        result['work_experiences'] = experiences
        confidence_scores.append(0.9 if experiences else 0.0)
        
        # 5. 提取当前职位和公司
        current_position_patterns = [
            r'(?:当前职位|现任)[：:]\s*([^\n]{2,30})',
            r'(?:高级|资深|初级|中级)?\s*(工程师|开发|架构师|经理|总监)',
        ]
        for pattern in current_position_patterns:
            match = re.search(pattern, text)
            if match:
                result['current_position'] = match.group(1).strip()
                confidence_scores.append(0.8)
                break
        else:
            confidence_scores.append(0.5)
        
        # 当前公司
        for company in self.companies:
            if company in text:
                result['current_company'] = company
                confidence_scores.append(0.8)
                break
        else:
            confidence_scores.append(0.5)
        
        # 6. 提取获奖荣誉
        awards_section = self._extract_section(
            text,
            ['获奖荣誉', '获奖经历', '奖项', '荣誉', '奖学金'],
            section_headers,
        )
        awards = []
        award_lines = self._section_lines(awards_section)
        trailing_date_pattern = re.compile(
            r'(?P<date>(?:19|20)\d{2}(?:[.\-/]\d{1,2})?)\s*$'
        )
        for line in award_lines:
            if awards and re.match(r'^(?:因|由于|在|通过|参与|负责|并且|同时)', line):
                previous = awards[-1].get('description', '')
                awards[-1]['description'] = f'{previous} {line}'.strip()
                continue

            date_match = trailing_date_pattern.search(line)
            award_date = date_match.group('date') if date_match else None
            content = line[:date_match.start()].rstrip(' -—–―－') if date_match else line
            parts = re.split(r'\s+[—–―－-]\s+', content, maxsplit=1)
            award = {
                'name': parts[0].strip(),
                'issuer': parts[1].strip() if len(parts) == 2 else None,
                'date': award_date,
                'description': '',
            }
            if award['name']:
                awards.append(award)

        result['awards'] = awards
        confidence_scores.append(0.8 if awards else 0.3)

        # 7. 提取项目经历
        project_section = self._extract_section(
            text,
            ['项目经历', '项目经验', '项目履历', '主要项目'],
            section_headers,
        )
        project_experiences = []
        project_lines = self._section_lines(project_section)
        for line in project_lines:
            project_match = re.match(
                r'(?:项目名称[：:]|[●•▪·]|\d+[.、])\s*(.+)',
                line,
            )
            if project_match:
                project_name = project_match.group(1).strip()
                if len(project_name) > 2:
                    project_experiences.append({'name': project_name})

        # 一些简历将“项目 + 获奖”写在获奖章节中，保留项目名避免信息丢失。
        if not project_experiences:
            for award in awards:
                if '项目' in award['name']:
                    project_experiences.append({
                        'name': award['name'],
                        'description': award.get('description', ''),
                        'achievements': [award.get('issuer')] if award.get('issuer') else [],
                    })

        result['project_experiences'] = project_experiences
        confidence_scores.append(0.8 if project_experiences else 0.5)

        # 8. 提取证书
        certifications = []
        cert_keywords = [
            'PMP', 'CPA', 'CFA', 'CISSP', 'AWS', 'Azure', 'GCP',
            '软考', '系统架构师', '网络工程师', '信息系统项目管理师',
            '英语四级', '英语六级', 'CET-4', 'CET-6', '雅思', '托福', 'IELTS', 'TOEFL'
        ]
        for cert in cert_keywords:
            if cert in text:
                certifications.append({'name': cert})
        
        if certifications:
            result['certifications'] = certifications
        else:
            result['certifications'] = []
        
        # 8. 提取语言能力
        languages = []
        lang_patterns = [
            (r'英语[：:]*\s*(流利|熟练|精通|一般|良好)', '英语'),
            (r'日语[：:]*\s*(流利|熟练|精通|一般|良好|N[1-5])', '日语'),
            (r'韩语[：:]*\s*(流利|熟练|精通|一般|良好)', '韩语'),
        ]
        for pattern, lang in lang_patterns:
            match = re.search(pattern, text)
            if match:
                languages.append({'language': lang, 'proficiency': match.group(1)})
        
        if '普通话' in text:
            languages.append({'language': '普通话', 'proficiency': '母语'})
        
        result['languages'] = languages
        
        # 9. 提取自我评价
        self_eval_match = re.search(
            r'(?:自我评价|个人简介|个人总结)[：:]?\s*(.*?)(?=工作经[历验]|项目经[历验]|教育背景|技能|$)',
            text, re.DOTALL | re.IGNORECASE
        )
        if self_eval_match:
            self_eval = self_eval_match.group(1).strip()[:500]
            if len(self_eval) > 10:
                result['self_evaluation'] = self_eval
        
        # 10. 提取链接
        links = {}
        github_match = re.search(r'github\.com/([A-Za-z0-9_-]+)', text, re.IGNORECASE)
        if github_match:
            links['github'] = f"https://github.com/{github_match.group(1)}"
        linkedin_match = re.search(r'linkedin\.com/in/([A-Za-z0-9_-]+)', text, re.IGNORECASE)
        if linkedin_match:
            links['linkedin'] = f"https://linkedin.com/in/{linkedin_match.group(1)}"
        if links:
            result['links'] = links
        
        # 11. 提取教育背景列表
        education_list = []
        edu_section_match = re.search(
            r'(?:教育背景|教育经历|学历)[：:]?(.*?)(?=工作经[历验]|项目经[历验]|技能|自我评价|获奖|证书|$)',
            text, re.DOTALL | re.IGNORECASE
        )
        if edu_section_match:
            edu_text = edu_section_match.group(1)
            edu_pattern = r'(\d{4}[.\-/年]?\d{0,2})\s*[-~至到]\s*(\d{4}[.\-/年]?\d{0,2}|至今|现在)?\s*([^\n]{2,30}(?:大学|学院|University|College)[^\n]{0,20})'
            for match in re.finditer(edu_pattern, edu_text):
                edu_entry = {
                    'start_date': match.group(1).strip(),
                    'end_date': match.group(2).strip() if match.group(2) else None,
                    'school': match.group(3).strip()
                }
                education_list.append(edu_entry)
        
        if not education_list and result.get('university'):
            education_list.append({'school': result.get('university'), 'degree': result.get('education')})
        
        if education_list:
            result['education_list'] = education_list
        else:
            result['education_list'] = []
        
        # 12. 计算总置信度
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        logger.info(f"规则提取完成，提取字段数: {len(result)}，置信度: {overall_confidence:.2f}")
        return result, overall_confidence
    
    def _extract_resume_by_llm(self, text: str) -> Tuple[Dict[str, Any], float, str]:
        """大模型提取简历"""
        logger.info("使用大模型提取简历")
        
        prompt = f"""
请从以下简历文本中提取完整的结构化信息，以JSON格式返回。请尽可能提取所有信息。

**简历文本：**
{text[:12000]}

**要求输出JSON格式（只返回JSON，不要其他文字）：**
{{
    "name": "姓名",
    "phone": "电话",
    "email": "邮箱",
    "age": 年龄(数字),
    "gender": "性别",
    "location": "所在城市",
    "years_experience": 工作年限(数字),
    "current_position": "当前职位",
    "current_company": "当前公司",
    
    "education_list": [
        {{
            "school": "学校名称",
            "major": "专业",
            "degree": "学历(博士/硕士/本科/专科)",
            "start_date": "入学时间(如2018-09)",
            "end_date": "毕业时间(如2022-06)",
            "gpa": "GPA(如有)",
            "achievements": "在校成就/荣誉(如有)"
        }}
    ],
    
    "work_experiences": [
        {{
            "company": "公司名称",
            "position": "职位",
            "department": "部门(如有)",
            "start_date": "开始时间",
            "end_date": "结束时间(在职则为'至今')",
            "location": "工作地点",
            "responsibilities": ["职责1", "职责2"],
            "achievements": ["业绩/成果1", "业绩/成果2"]
        }}
    ],
    
    "project_experiences": [
        {{
            "name": "项目名称",
            "role": "担任角色",
            "company": "所属公司(如有)",
            "start_date": "开始时间",
            "end_date": "结束时间",
            "tech_stack": ["技术1", "技术2"],
            "description": "项目描述",
            "responsibilities": ["我的职责1", "我的职责2"],
            "achievements": ["项目成果/亮点"]
        }}
    ],
    
    "skills": {{
        "programming_languages": ["编程语言"],
        "frameworks": ["框架"],
        "databases": ["数据库"],
        "tools": ["工具/平台"],
        "other": ["其他技能"]
    }},
    
    "certifications": [
        {{
            "name": "证书名称",
            "issuer": "颁发机构",
            "date": "获得时间",
            "credential_id": "证书编号(如有)"
        }}
    ],
    
    "languages": [
        {{
            "language": "语言",
            "proficiency": "熟练程度(母语/流利/熟练/一般)"
        }}
    ],
    
    "awards": [
        {{
            "name": "奖项名称",
            "issuer": "颁发机构",
            "date": "获奖时间",
            "description": "描述(如有)"
        }}
    ],
    
    "publications": [
        {{
            "title": "论文/专利标题",
            "type": "类型(论文/专利/著作)",
            "date": "发表时间",
            "description": "描述"
        }}
    ],
    
    "social_activities": [
        {{
            "organization": "组织名称",
            "role": "角色",
            "period": "时间段",
            "description": "描述"
        }}
    ],
    
    "job_intention": {{
        "positions": ["期望职位"],
        "industries": ["期望行业"],
        "cities": ["期望城市"],
        "salary_min": 期望最低薪资(数字,单位K),
        "salary_max": 期望最高薪资(数字,单位K),
        "job_type": "工作类型(全职/兼职/实习)"
    }},
    
    "self_evaluation": "自我评价",
    
    "links": {{
        "github": "GitHub链接",
        "linkedin": "LinkedIn链接",
        "portfolio": "个人网站/作品集",
        "blog": "博客"
    }}
}}

**提取要求：**
1. 如果某个字段找不到，设为 null（数组字段设为空数组 []）
2. 日期格式统一为 "YYYY-MM" 或 "YYYY"
3. 工作经历和项目经历按时间倒序排列（最近的在前）
4. 技能尽量分类到对应类别
5. 提取所有能找到的信息，不要遗漏
"""
        
        try:
            async def call_llm():
                return await self.openai_service.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    json_mode=True
                )
            
            # 检查是否在异步上下文中
            try:
                loop = asyncio.get_running_loop()
                # 已经在异步上下文中，使用线程池执行
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, call_llm())
                    content = future.result()
            except RuntimeError:
                # 没有运行中的事件循环，直接运行
                content = asyncio.run(call_llm())
            
            # chat_completion 返回字符串
            content = content.strip()
            # 去掉可能的markdown代码块标记
            if content.startswith('```'):
                content = re.sub(r'```json\n|```\n|```', '', content).strip()
            
            structured_data = json.loads(content)
            
            # 大模型提取置信度默认0.95
            return structured_data, 0.95, 'llm'
        
        except Exception as e:
            logger.error(f"大模型提取失败: {e}")
            # 失败回退到规则提取
            data, conf = self._extract_resume_by_rules(text)
            return data, conf, 'rule'
    
    def extract_job(
        self,
        text: str,
        use_llm: bool = False,
        force_llm: bool = False
    ) -> Tuple[Dict[str, Any], float, str]:
        """
        提取职位结构化数据
        
        Args:
            text: 职位描述文本
            use_llm: 是否允许使用大模型
            force_llm: 是否强制使用大模型
        
        Returns:
            (structured_data, confidence, method)
        """
        logger.info(f"开始提取职位，长度: {len(text)}，use_llm={use_llm}, force_llm={force_llm}")
        
        if force_llm and use_llm:
            return self._extract_job_by_llm(text)
        
        # 规则提取
        structured_data, confidence = self._extract_job_by_rules(text)
        
        if confidence >= 0.7:
            return structured_data, confidence, 'rule'
        
        if use_llm and confidence < 0.7:
            logger.warning(f"职位规则提取置信度低 ({confidence})，调用大模型")
            return self._extract_job_by_llm(text)
        
        return structured_data, confidence, 'rule'
    
    def _extract_job_by_rules(self, text: str) -> Tuple[Dict[str, Any], float]:
        """规则提取职位"""
        result = {}
        confidence_scores = []
        
        # 1. 职位名称（通常在第一行或标题）
        title_patterns = [
            r'(?:职位名称|岗位名称|招聘职位)[：:]\s*([^\n]{2,50})',
            r'^([^\n]{2,30}(?:工程师|开发|经理|总监|架构师))',
        ]
        for pattern in title_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                result['title'] = match.group(1).strip()
                confidence_scores.append(1.0)
                break
        else:
            confidence_scores.append(0.0)
        
        # 2. 公司名称
        company_patterns = [
            r'(?:公司名称|公司)[：:]\s*([^\n]{2,50})',
        ]
        for company in self.companies:
            if company in text:
                result['company'] = company
                confidence_scores.append(1.0)
                break
        else:
            for pattern in company_patterns:
                match = re.search(pattern, text)
                if match:
                    result['company'] = match.group(1).strip()
                    confidence_scores.append(0.8)
                    break
            else:
                confidence_scores.append(0.0)
        
        # 3. 工作城市
        city_keywords = [
            '北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京',
            '西安', '苏州', '重庆', '天津', '长沙', '厦门', '青岛', '大连'
        ]
        for city in city_keywords:
            if city in text:
                result['city'] = city
                confidence_scores.append(1.0)
                break
        else:
            confidence_scores.append(0.3)
        
        # 4. 薪资范围
        salary_patterns = [
            r'(\d+)[kK][-~]\s*(\d+)[kK]',  # 15k-25k
            r'(\d+)[-~]\s*(\d+)[万千]',     # 15-25万
        ]
        for pattern in salary_patterns:
            match = re.search(pattern, text)
            if match:
                min_sal = int(match.group(1))
                max_sal = int(match.group(2))
                result['salary_range'] = f"{min_sal}k-{max_sal}k"
                result['salary_min'] = min_sal
                result['salary_max'] = max_sal
                confidence_scores.append(1.0)
                break
        else:
            confidence_scores.append(0.5)
        
        # 5. 经验要求
        exp_patterns = [
            r'(\d+)\s*[年\+]\s*(?:以上)?(?:工作)?经验',
            r'(\d+)[-~](\d+)\s*年',
        ]
        for pattern in exp_patterns:
            match = re.search(pattern, text)
            if match:
                result['experience_required'] = match.group(0).strip()
                confidence_scores.append(1.0)
                break
        else:
            if '应届' in text or '不限' in text:
                result['experience_required'] = '应届/不限'
                confidence_scores.append(1.0)
            else:
                confidence_scores.append(0.3)
        
        # 6. 学历要求
        edu_keywords = ['博士', '硕士', '本科', '专科', '不限']
        for edu in edu_keywords:
            if edu in text:
                result['education_required'] = edu
                confidence_scores.append(1.0)
                break
        else:
            confidence_scores.append(0.5)
        
        # 7. 技能要求
        required_skills = []
        preferred_skills = []
        
        for skill in self.all_skills:
            if skill in text or skill.lower() in text.lower():
                # 判断是必备还是加分
                if '熟悉' in text or '掌握' in text or '精通' in text:
                    required_skills.append(skill)
                else:
                    preferred_skills.append(skill)
        
        if required_skills:
            result['required_skills'] = list(set(required_skills))
            confidence_scores.append(min(len(required_skills) / 5, 1.0))
        else:
            confidence_scores.append(0.3)
        
        if preferred_skills:
            result['preferred_skills'] = list(set(preferred_skills))
        
        # 8. 岗位职责
        responsibilities = []
        resp_section = re.search(
            r'(?:岗位职责|工作内容|职位描述)[：:](.*?)(?=任职要求|岗位要求|技能要求|$)',
            text,
            re.DOTALL
        )
        if resp_section:
            resp_text = resp_section.group(1)
            # 按行拆分
            lines = [line.strip() for line in resp_text.split('\n') if line.strip()]
            for line in lines[:10]:  # 最多10条
                if len(line) > 5 and len(line) < 200:
                    responsibilities.append(line)
            
            if responsibilities:
                result['responsibilities'] = responsibilities
                confidence_scores.append(0.9)
            else:
                confidence_scores.append(0.3)
        else:
            confidence_scores.append(0.0)
        
        # 9. 福利待遇
        benefits_keywords = [
            '五险一金', '六险一金', '年终奖', '股票期权', '带薪年假',
            '弹性工作', '远程办公', '下午茶', '健身房', '免费午餐', '班车'
        ]
        benefits = [b for b in benefits_keywords if b in text]
        if benefits:
            result['benefits'] = benefits
            confidence_scores.append(0.8)
        else:
            confidence_scores.append(0.5)
        
        # 10. 计算总置信度
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        logger.info(f"职位规则提取完成，字段数: {len(result)}，置信度: {overall_confidence:.2f}")
        return result, overall_confidence
    
    def _extract_job_by_llm(self, text: str) -> Tuple[Dict[str, Any], float, str]:
        """大模型提取职位"""
        logger.info("使用大模型提取职位")
        
        prompt = f"""
请从以下职位描述中提取结构化信息，以JSON格式返回。

**职位描述：**
{text[:3000]}

**要求输出JSON格式（只返回JSON）：**
{{
    "title": "职位名称",
    "company": "公司名称",
    "city": "工作城市",
    "salary_range": "薪资范围",
    "experience_required": "经验要求",
    "education_required": "学历要求",
    "required_skills": ["必备技能1", "必备技能2"],
    "preferred_skills": ["加分技能1", "加分技能2"],
    "responsibilities": ["职责1", "职责2"],
    "benefits": ["福利1", "福利2"],
    "company_size": "公司规模",
    "company_industry": "公司行业"
}}

如果某个字段找不到，请设为 null。
"""
        
        try:
            async def call_llm():
                return await self.openai_service.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    json_mode=True
                )
            
            # 检查是否在异步上下文中
            try:
                loop = asyncio.get_running_loop()
                # 已经在异步上下文中，使用线程池执行
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, call_llm())
                    content = future.result()
            except RuntimeError:
                # 没有运行中的事件循环，直接运行
                content = asyncio.run(call_llm())
            
            content = content.strip()
            if content.startswith('```'):
                content = re.sub(r'```json\n|```\n|```', '', content).strip()
            
            structured_data = json.loads(content)
            return structured_data, 0.95, 'llm'
        
        except Exception as e:
            logger.error(f"大模型提取职位失败: {e}")
            data, conf = self._extract_job_by_rules(text)
            return data, conf, 'rule'
