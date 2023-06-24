import argparse
import dataclasses
from dataclasses import dataclass
from typing import Optional, Tuple
from aphrodite.common.config import CacheConfig, ModelConfig, PretrainedConfig, SchedulerConfig


@dataclass
class EngineArgs:
    """Arguments and flags for the Aphrodite Engine"""
    model: str
    download_dir: Optional[str] = None
    use_np_weights: bool = False
    use_dummy_weights: bool = False
    dtype: str = "auto"
    seed: int = 42
    worker_use_ray: bool = False
    pipeline_parallel_size: int = 1
    tensor_parallel_size: int = 1
    block_size: int = 16
    swap_space: int = 4 # in GiB
    gpu_memory_utilization: float = 0.88
    max_num_batched_tokens: int = 2560
    max_num_seqs: int = 256
    disable_log_stats: bool = False

    def __post_init__(self):
        self.max_num_seqs = min(self.max_num_seqs, self.max_num_batched_tokens)

    @staticmethod
    def add_cli_args(
        parser: argparse.ArgumentParser,
    ) -> argparse.ArgumentParser:
        # Model arguments
        parser.add_argument('--model', type=str, default='PygmalionAI/pygmalion-6b', help='name or path of the huggingface model.')
        parser.add_argument('--download-dir', type=str, default=EngineArgs.download_dir, help='directory to download the model to. Default is HF cache directory.')
        parser.add_argument('--use-np-weights', action='store_true', help='save a numpy copy of the model for faster loading. Increases disk space usage.')
        parser.add_argument('--use-dummy-weights', action='store_true', help='use dummy values for model weights.')
        parser.add_argument('--dtype', type=str, default=EngineArgs.dtype, choices=['auto', 'half', 'bfloat16', 'float'], help='datatype for the model weights. The "auto" option will use BF16 precision if compatible.')
        # Parallel arguments
        parser.add_argument('--worker-use-ray', action='store_true', help='use Ray for distributed inference. Will be automatically set if using more than one GPU.')
        parser.add_argument('--pipeline-parallel-size', '-pp', type=int, default=EngineArgs.pipeline_parallel_size, help='number of pipeline stages.')
        parser.add_argument('--tensor-parallel-size', '-tp', type=int, default=EngineArgs.tensor_parallel_size, help='number of tensor parallel replicas.')
        # KV cache arguments
        parser.add_argument('--block-size', type=int, default=EngineArgs.block_size, choices=[8, 16, 32], help='token block size.')
        parser.add_argument('--seed', type=int, default=EngineArgs.seed, help='random seed for requests')
        parser.add_argument('--swap-space', type=int, default=EngineArgs.swap_space, help='CPU swap space size (in GiB) per GPU')
        parser.add_argument('--gpu-memory-utilization', type=float, default=EngineArgs.gpu_memory_utilization, help='the percentage of GPU memory to be used for the model')
        parser.add_argument('--max-num-batched-tokens', type=int, default=EngineArgs.max_num_batched_tokens, help='maximum number of batched tokens per iteration.')
        parser.add_argument('--max-num-seqs', type=int, default=EngineArgs.max_num_seqs, help='maximum number of sequences per iteration.')
        parser.add_argument('--disable-log-stats', action='store_true', help='disable logging statistics')
        return parser

    @classmethod
    def from_cli_args(cls, args: argparse.Namespace) -> "EngineArgs":
        attrs = [attr.name for attr in dataclasses.fields(cls)]
        engine_args = cls(**{attr: getattr(args, attrs) for attr in attrs})
        return engine_args

    def create_engine_configs(
        self,
    ) -> Tuple[ModelConfig, CacheConfig, ParallelConfig, SchedulerConfig]:
        model_config = ModelConfig(
            self.model, self.download_dir, self.use_np_weights, self.use_dummy_weights, self.dtype, self.seed)
        cache_config = CacheConfig(self.block_size, self.gpu_memory_utilization, self.swap_space)
        parallel_config = ParallelConfig(self.pipeline_parallel_size, self.tensor_parallel_size, self.worker_use_ray)
        scheduler_config = SchedulerConfig(self.max_num_batched_tokens, self.max_num_seqs)
        return model_config, cache_config, parallel_config, scheduler_config
