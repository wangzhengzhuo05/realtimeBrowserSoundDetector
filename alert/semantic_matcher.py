# -*- coding: utf-8 -*-
"""
语义匹配模块
使用阿里云 DashScope 文本嵌入模型进行语义相似度匹配
"""

import numpy as np
import threading
import concurrent.futures
from typing import List, Tuple, Optional, Dict
from colorama import Fore, Style

try:
    from dashscope import TextEmbedding
except ImportError:
    TextEmbedding = None
    print(f"{Fore.YELLOW}[警告] 请安装 dashscope: pip install dashscope{Style.RESET_ALL}")


class SemanticMatcher:
    """
    语义匹配器
    使用文本嵌入模型计算语义相似度
    """
    
    def __init__(self, api_key: str, keywords: List[str], threshold: float = 0.65, model: str = "text-embedding-v3"):
        """
        :param api_key: DashScope API Key
        :param keywords: 关键词列表
        :param threshold: 相似度阈值 (0-1)，越高越严格
        """
        self.api_key = api_key
        self.keywords = keywords
        self.threshold = threshold
        self.model = model
        self.keyword_embeddings: Dict[str, np.ndarray] = {}  # 关键词向量缓存
        self.phrase_embedding_cache: Dict[str, np.ndarray] = {}  # 片段向量缓存
        self._cache_lock = threading.Lock()
        self.cache_max_size = 300
        self.enabled = False
        
        if not TextEmbedding:
            print(f"{Fore.YELLOW}[警告] DashScope 未安装，语义匹配已禁用{Style.RESET_ALL}")
            return
        
        if not api_key:
            print(f"{Fore.YELLOW}[警告] API Key 未配置，语义匹配已禁用{Style.RESET_ALL}")
            return
        
        # 预计算关键词向量
        self._init_keyword_embeddings()
    
    def _init_keyword_embeddings(self):
        """初始化关键词向量"""
        try:
            print(f"{Fore.CYAN}[语义] 正在初始化关键词向量...{Style.RESET_ALL}")
            
            # 批量获取关键词向量
            response = TextEmbedding.call(
                model=self.model,
                input=self.keywords,
                api_key=self.api_key
            )
            
            if response.status_code == 200:
                embeddings = response.output.get("embeddings", [])
                for i, keyword in enumerate(self.keywords):
                    if i < len(embeddings):
                        self.keyword_embeddings[keyword] = np.array(embeddings[i]["embedding"])
                
                self.enabled = True
                print(f"{Fore.GREEN}[语义] 已加载 {len(self.keyword_embeddings)} 个关键词向量，相似度阈值: {self.threshold}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}[警告] 获取关键词向量失败: {response.message}{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.YELLOW}[警告] 初始化语义匹配失败: {e}{Style.RESET_ALL}")
    
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """获取文本向量"""
        try:
            response = TextEmbedding.call(
                model=self.model,
                input=[text],
                api_key=self.api_key
            )
            
            if response.status_code == 200:
                embeddings = response.output.get("embeddings", [])
                if embeddings:
                    return np.array(embeddings[0]["embedding"])
        except Exception as e:
            pass
        
        return None

    def _get_embeddings_batch(self, phrases: List[str]) -> Dict[str, np.ndarray]:
        """批量获取短语向量并带缓存，DashScope 单次最多10条，多批并发"""
        results: Dict[str, np.ndarray] = {}

        # 去重，防止重复请求
        unique_phrases = list(dict.fromkeys(phrases))

        # 先取缓存
        with self._cache_lock:
            for phrase in unique_phrases:
                if phrase in self.phrase_embedding_cache:
                    results[phrase] = self.phrase_embedding_cache[phrase]

        # 找出未缓存的短语
        uncached = [p for p in unique_phrases if p not in results]
        if not uncached:
            return results

        # DashScope 限制 batch <= 10
        batch_size = 10
        chunks = [uncached[i:i + batch_size] for i in range(0, len(uncached), batch_size)]

        def fetch_chunk(chunk: List[str]) -> List[Tuple[str, np.ndarray]]:
            """请求单个批次"""
            try:
                response = TextEmbedding.call(
                    model=self.model,
                    input=chunk,
                    api_key=self.api_key
                )
                if response.status_code == 200:
                    embeddings = response.output.get("embeddings", [])
                    return [(chunk[i], np.array(embeddings[i]["embedding"])) 
                            for i in range(min(len(chunk), len(embeddings)))]
            except Exception:
                pass
            return []

        # 并发请求所有批次
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(chunks))) as executor:
            futures = [executor.submit(fetch_chunk, chunk) for chunk in chunks]
            for future in concurrent.futures.as_completed(futures):
                for phrase, vec in future.result():
                    results[phrase] = vec
                    self._save_phrase_cache(phrase, vec)

        return results

    def _save_phrase_cache(self, phrase: str, vec: np.ndarray):
        """写入片段向量缓存，控制大小"""
        with self._cache_lock:
            # 如果超出容量，随机弹出一个最旧键（简单策略）
            if len(self.phrase_embedding_cache) >= self.cache_max_size:
                # pop first inserted item
                first_key = next(iter(self.phrase_embedding_cache))
                self.phrase_embedding_cache.pop(first_key, None)
            self.phrase_embedding_cache[phrase] = vec
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def find_similar_keywords(self, text: str) -> List[Tuple[str, float]]:
        """
        在文本中查找语义相似的关键词
        
        :param text: 待匹配的文本
        :return: 匹配到的关键词及其相似度列表 [(keyword, similarity), ...]
        """
        if not self.enabled or not self.keyword_embeddings:
            return []
        
        # 对文本进行分段匹配（滑动窗口）
        matches = []
        
        # 提取可能的短语（2-6个字的滑动窗口）
        phrases = self._extract_phrases(text)
        
        phrase_embeddings = self._get_embeddings_batch(phrases)

        for phrase, embedding in phrase_embeddings.items():
            
            # 与每个关键词计算相似度
            for keyword, kw_embedding in self.keyword_embeddings.items():
                similarity = self._cosine_similarity(embedding, kw_embedding)
                
                if similarity >= self.threshold:
                    # 避免重复添加
                    if not any(kw == keyword for kw, _ in matches):
                        matches.append((keyword, similarity))
                        print(f"{Fore.MAGENTA}[语义] 匹配: '{phrase}' ≈ '{keyword}' (相似度: {similarity:.2f}){Style.RESET_ALL}")
        
        return matches
    
    def _extract_phrases(self, text: str, min_len: int = 2, max_len: int = 4) -> List[str]:
        """
        从文本中提取短语
        使用滑动窗口提取不同长度的短语，限制数量以提高速度
        """
        phrases = []
        text = text.strip()
        
        if len(text) < min_len:
            return [text] if text else []
        
        # 只取最后 15 个字符做滑动窗口（减少短语数量）
        recent_text = text[-15:] if len(text) > 15 else text
        
        # 滑动窗口提取短语（2-4字，比原来 2-6 更少）
        for length in range(min_len, min(max_len + 1, len(recent_text) + 1)):
            for i in range(len(recent_text) - length + 1):
                phrase = recent_text[i:i + length]
                if phrase and phrase not in phrases:
                    phrases.append(phrase)
        
        # 限制最多 20 个短语
        if len(phrases) > 20:
            phrases = phrases[:20]
        
        return phrases
    
    def update_keywords(self, keywords: List[str]):
        """更新关键词列表"""
        self.keywords = keywords
        self.keyword_embeddings = {}
        if self.api_key:
            self._init_keyword_embeddings()
    
    def set_threshold(self, threshold: float):
        """设置相似度阈值"""
        self.threshold = max(0.0, min(1.0, threshold))
        print(f"{Fore.CYAN}[语义] 相似度阈值已更新为: {self.threshold}{Style.RESET_ALL}")
