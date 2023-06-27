#include <torch/extension.h>
#include <ATen/cuda/CUDAContext.h>

#include "reduction_utils.cuh"

namespace aphrodite {
template<typename scalar_t>
__global__ void rms_norm_kernel(
    scalar_t* __restrict__ out,
    const scalar_t* __restrict__ input,
    const scalar_t* __restrict__ weight,
    const float epsilon,
    const int num_tokens,
    const int hidden_size) {
    __shared__ float s_variance;
    float variance = 0.0f;

    for (int idx = threadIdx.x; idx < hidden_size; idx += blockDim.x) {
        const float x = (float) input[blockIdx.x * hidden_size + idx];
        variance += x * x;
    }
    variance = blockReduceSum<float>(variance);
    if (threadIdx.x == 0) {
        s_variance = rsqrtf(variance / hidden_size + epsilon);
    }
    __syncthreads();

    for (int idx = threadIdx.x; idx < hidden_size; idx += blockDim.x) {
        float x = (float) input[blockIdx.x * hidden_size + idx];
        out[blockIdx.x * hidden_size + idx] = ((scalar_t) (x * s_variance)) * weight[idx];
    }
}
}

void rms_norm(
    torch::Tensor& out,
    torch::Tensor& input,
    torch::Tensor& weight,
    float epsilon) {
    int num_tokens = input.size(0);
    int hidden_size = input.size(1);

    dim3 grid(num_tokens);
    dim3 block(std::min(hidden_size, 1024));
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream();
    AT_DISPATCH_FLOATING_TYPES_AND2(
        at::ScalarType::Half,
        at::ScalarType::BFloat16,
        input.scalar_type(),
        "rms_norm_kernel",
        [&] {
            aphrodite::rms_norm_kernel<scalar_t><<<grid, block, 0, stream>>>(
                out.data_ptr<scalar_t>(),
                input.data_ptr<scalar_t>(),
                weight.data_ptr<scalar_t>(),
                epsilon,
                num_tokens,
                hidden_size);
        });
}