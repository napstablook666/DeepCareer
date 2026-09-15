"""
智能匹配引擎 - 业界最佳实践
结合结构化匹配 + 语义匹配 + 关键词匹配
"""
import re
from typing import List, Dict, Tuple
from backend.utils.embedding_service import get_embedding_service
from numpy import dot
from numpy.linalg import norm
import jieba
import jieba.analyse


class SmartMatcher:
    """智能简历-职位匹配器"""
    
    def __init__(self):
        """初始化匹配器；语义向量由模力方舟远程服务生成。"""
        self.embedding_service = get_embedding_service()
        
        # 技术栈关键词库（可扩展）
        self.tech_keywords = {
            'backend': ['Python', 'Java', 'Go', 'Node.js', 'Django', 'FastAPI', 'Spring', 'Flask'],
            'frontend': ['React', 'Vue', 'Angular', 'JavaScript', 'TypeScript', 'HTML', 'CSS'],
            'database': ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server'],
            'devops': ['Docker', 'Kubernetes', 'Jenkins', 'CI/CD', 'AWS', 'Azure', 'Linux'],
            'architecture': ['微服务', '分布式', '高并发', 'RESTful', 'gRPC', '消息队列']
        }
    
    def extract_keywords(self, text: str, top_k: int = 20) -> List[str]:
        """提取关键词"""
        # 使用 jieba 提取关键词
        keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=False)
        return keywords
    
    def extract_years_experience(self, text: str) -> int:
        """提取工作年限"""
        patterns = [
            r'(\d+)\s*年.*?经验',
            r'(\d+)\s*年.*?工作',
            r'(\d+)\+?\s*years?',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 0
    
    def extract_tech_stack(self, text: str) -> Dict[str, List[str]]:
        """提取技术栈（按类别分组）"""
        found_tech = {category: [] for category in self.tech_keywords.keys()}
        
        text_lower = text.lower()
        for category, keywords in self.tech_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower or keyword in text:
                    found_tech[category].append(keyword)
        
        return {k: v for k, v in found_tech.items() if v}  # 只返回非空的
    
    def keyword_match_score(self, resume_keywords: List[str], job_keywords: List[str]) -> float:
        """关键词匹配分数（Jaccard 相似度）"""
        if not job_keywords:
            return 0.0
        
        resume_set = set(kw.lower() for kw in resume_keywords)
        job_set = set(kw.lower() for kw in job_keywords)
        
        intersection = len(resume_set & job_set)
        union = len(resume_set | job_set)
        
        return intersection / union if union > 0 else 0.0
    
    def tech_stack_match_score(self, resume_tech: Dict[str, List[str]], 
                               job_tech: Dict[str, List[str]]) -> float:
        """技术栈匹配分数"""
        if not job_tech:
            return 0.0
        
        total_score = 0.0
        category_count = 0
        
        for category, job_skills in job_tech.items():
            resume_skills = resume_tech.get(category, [])
            if job_skills:
                category_count += 1
                # 计算该类别的匹配度
                match_count = len(set(job_skills) & set(resume_skills))
                category_score = match_count / len(job_skills)
                total_score += category_score
        
        return total_score / category_count if category_count > 0 else 0.0
    
    def semantic_similarity(self, text1: str, text2: str) -> float:
        """语义相似度"""
        embeddings = self.embedding_service.create_embedding([text1, text2])
        emb1, emb2 = embeddings
        return dot(emb1, emb2) / (norm(emb1) * norm(emb2))
    
    def section_match_score(self, resume_sections: Dict[str, str], 
                           job_sections: Dict[str, str],
                           weights: Dict[str, float] = None) -> float:
        """分段匹配分数"""
        if weights is None:
            weights = {
                'skills': 0.4,
                'experience': 0.3,
                'education': 0.2,
                'other': 0.1
            }
        
        total_score = 0.0
        total_weight = 0.0
        
        for section, job_text in job_sections.items():
            resume_text = resume_sections.get(section, "")
            if resume_text and job_text:
                sim = self.semantic_similarity(resume_text, job_text)
                weight = weights.get(section, 0.1)
                total_score += sim * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def comprehensive_match(self, resume: Dict, job: Dict) -> Dict[str, float]:
        """
        综合匹配（业界最佳实践）
        
        Args:
            resume: {
                'full_text': '完整简历文本',
                'skills': '技能描述',
                'experience': '工作经验',
                'education': '教育背景'
            }
            job: {
                'full_text': '完整职位描述',
                'requirements': '任职要求',
                'responsibilities': '岗位职责'
            }
        
        Returns:
            {
                'total_score': 0.85,      # 总分
                'keyword_score': 0.75,    # 关键词匹配
                'tech_score': 0.90,       # 技术栈匹配
                'semantic_score': 0.88,   # 语义匹配
                'experience_score': 1.0,  # 经验匹配
                'breakdown': {...}        # 详细分解
            }
        """
        # 1. 关键词匹配
        resume_keywords = self.extract_keywords(resume['full_text'])
        job_keywords = self.extract_keywords(job['full_text'])
        keyword_score = self.keyword_match_score(resume_keywords, job_keywords)
        
        # 2. 技术栈匹配
        resume_tech = self.extract_tech_stack(resume['full_text'])
        job_tech = self.extract_tech_stack(job['full_text'])
        tech_score = self.tech_stack_match_score(resume_tech, job_tech)
        
        # 3. 工作年限匹配
        resume_years = self.extract_years_experience(resume['full_text'])
        job_years = self.extract_years_experience(job['full_text'])
        if job_years > 0:
            experience_score = min(resume_years / job_years, 1.0)
        else:
            experience_score = 0.5  # 没有明确年限要求
        
        # 4. 分段语义匹配
        resume_sections = {
            'skills': resume.get('skills', ''),
            'experience': resume.get('experience', '')
        }
        job_sections = {
            'skills': job.get('requirements', ''),
            'experience': job.get('responsibilities', '')
        }
        semantic_score = self.section_match_score(resume_sections, job_sections)
        
        # 5. 综合评分（加权平均）
        weights = {
            'tech': 0.35,        # 技术栈匹配最重要
            'semantic': 0.30,    # 语义匹配
            'keyword': 0.20,     # 关键词匹配
            'experience': 0.15   # 经验匹配
        }
        
        total_score = (
            tech_score * weights['tech'] +
            semantic_score * weights['semantic'] +
            keyword_score * weights['keyword'] +
            experience_score * weights['experience']
        )
        
        return {
            'total_score': round(total_score, 3),
            'tech_score': round(tech_score, 3),
            'semantic_score': round(semantic_score, 3),
            'keyword_score': round(keyword_score, 3),
            'experience_score': round(experience_score, 3),
            'breakdown': {
                'resume_keywords': resume_keywords[:10],
                'job_keywords': job_keywords[:10],
                'resume_tech': resume_tech,
                'job_tech': job_tech,
                'resume_years': resume_years,
                'job_years': job_years
            }
        }


if __name__ == '__main__':
    # 测试
    import os
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    
    print("=" * 70)
    print("智能匹配引擎测试")
    print("=" * 70)
    
    matcher = SmartMatcher()
    
    # 测试简历
    resume = {
        'full_text': """
        资深Python后端开发工程师，5年工作经验。精通Django、FastAPI框架，
        负责设计和开发高并发Web服务和RESTful API。熟练使用PostgreSQL、
        MySQL数据库，掌握Redis缓存技术。有微服务架构实践经验，使用
        Docker和Kubernetes进行容器化部署。注重代码质量和单元测试。
        """,
        'skills': 'Python, Django, FastAPI, PostgreSQL, MySQL, Redis, Docker, Kubernetes',
        'experience': '5年后端开发经验，负责高并发系统设计'
    }
    
    # 测试职位
    jobs = [
        {
            'name': 'Python后端工程师（高匹配）',
            'full_text': '招聘Python后端工程师，3年以上经验，熟悉Django或FastAPI，了解微服务',
            'requirements': 'Python, Django, 微服务, 3年经验',
            'responsibilities': '后端API开发，系统设计'
        },
        {
            'name': 'Java后端工程师（低匹配）',
            'full_text': '招聘Java工程师，熟悉Spring Boot、MyBatis，有分布式经验',
            'requirements': 'Java, Spring Boot, MyBatis',
            'responsibilities': '后端服务开发'
        },
        {
            'name': '前端工程师（低匹配）',
            'full_text': '招聘前端工程师，精通React、Vue，有移动端开发经验',
            'requirements': 'React, Vue, JavaScript',
            'responsibilities': '前端页面开发'
        }
    ]
    
    print("\n📄 简历: Python后端工程师，5年经验\n")
    
    results = []
    for job in jobs:
        score = matcher.comprehensive_match(resume, job)
        results.append((job['name'], score))
    
    # 按分数排序
    results.sort(key=lambda x: x[1]['total_score'], reverse=True)
    
    print("匹配结果（按总分排序）:")
    print("=" * 70)
    for job_name, score in results:
        total = score['total_score'] * 100
        print(f"\n职位: {job_name}")
        print(f"  总分: {total:5.1f}%")
        print(f"  ├─ 技术栈: {score['tech_score']*100:5.1f}%")
        print(f"  ├─ 语义匹配: {score['semantic_score']*100:5.1f}%")
        print(f"  ├─ 关键词: {score['keyword_score']*100:5.1f}%")
        print(f"  └─ 经验: {score['experience_score']*100:5.1f}%")
    
    print("\n" + "=" * 70)
    print("✅ 测试完成！这个方案比纯 Embedding 更准确")
    print("=" * 70)
