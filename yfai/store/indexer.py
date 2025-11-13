"""向量索引管理模块

用于知识库RAG的向量存储和检索
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np


class VectorIndexer:
    """向量索引器"""

    def __init__(self, index_path: str = "data/vectors", dimension: int = 1536):
        """初始化向量索引器

        Args:
            index_path: 索引文件路径
            dimension: 向量维度（默认1536，DashScope text-embedding-v1）
        """
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self.indexes: Dict[str, faiss.IndexFlatL2] = {}
        self.metadata: Dict[str, List[Dict[str, Any]]] = {}

    def create_index(self, kb_id: str) -> None:
        """创建新的索引

        Args:
            kb_id: 知识库ID
        """
        index = faiss.IndexFlatL2(self.dimension)
        self.indexes[kb_id] = index
        self.metadata[kb_id] = []

    def add_vectors(
        self, kb_id: str, vectors: np.ndarray, metadatas: List[Dict[str, Any]]
    ) -> None:
        """添加向量到索引

        Args:
            kb_id: 知识库ID
            vectors: 向量数组 (n, dimension)
            metadatas: 元数据列表
        """
        if kb_id not in self.indexes:
            self.create_index(kb_id)

        index = self.indexes[kb_id]
        index.add(vectors.astype("float32"))

        # 保存元数据
        if kb_id not in self.metadata:
            self.metadata[kb_id] = []
        self.metadata[kb_id].extend(metadatas)

    def search(
        self, kb_id: str, query_vector: np.ndarray, top_k: int = 5
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """检索最相似的向量

        Args:
            kb_id: 知识库ID
            query_vector: 查询向量 (1, dimension)
            top_k: 返回前k个结果

        Returns:
            [(距离, 元数据), ...]
        """
        if kb_id not in self.indexes:
            return []

        index = self.indexes[kb_id]
        if index.ntotal == 0:
            return []

        # 搜索
        query_vector = query_vector.reshape(1, -1).astype("float32")
        distances, indices = index.search(query_vector, min(top_k, index.ntotal))

        # 组合结果
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata[kb_id]):
                results.append((float(dist), self.metadata[kb_id][idx]))

        return results

    def save(self, kb_id: str) -> None:
        """保存索引到磁盘

        Args:
            kb_id: 知识库ID
        """
        if kb_id not in self.indexes:
            return

        # 保存FAISS索引
        index_file = self.index_path / f"{kb_id}.index"
        faiss.write_index(self.indexes[kb_id], str(index_file))

        # 保存元数据
        metadata_file = self.index_path / f"{kb_id}.meta.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata[kb_id], f, ensure_ascii=False, indent=2)

    def load(self, kb_id: str) -> bool:
        """从磁盘加载索引

        Args:
            kb_id: 知识库ID

        Returns:
            是否加载成功
        """
        index_file = self.index_path / f"{kb_id}.index"
        metadata_file = self.index_path / f"{kb_id}.meta.json"

        if not index_file.exists() or not metadata_file.exists():
            return False

        try:
            # 加载FAISS索引
            self.indexes[kb_id] = faiss.read_index(str(index_file))

            # 加载元数据
            with open(metadata_file, "r", encoding="utf-8") as f:
                self.metadata[kb_id] = json.load(f)

            return True
        except Exception as e:
            print(f"加载索引失败: {e}")
            return False

    def delete(self, kb_id: str) -> None:
        """删除索引

        Args:
            kb_id: 知识库ID
        """
        # 从内存删除
        self.indexes.pop(kb_id, None)
        self.metadata.pop(kb_id, None)

        # 从磁盘删除
        index_file = self.index_path / f"{kb_id}.index"
        metadata_file = self.index_path / f"{kb_id}.meta.json"

        if index_file.exists():
            index_file.unlink()
        if metadata_file.exists():
            metadata_file.unlink()

    def get_stats(self, kb_id: str) -> Optional[Dict[str, Any]]:
        """获取索引统计信息

        Args:
            kb_id: 知识库ID

        Returns:
            统计信息字典
        """
        if kb_id not in self.indexes:
            return None

        index = self.indexes[kb_id]
        return {
            "kb_id": kb_id,
            "total_vectors": index.ntotal,
            "dimension": self.dimension,
            "metadata_count": len(self.metadata.get(kb_id, [])),
        }

