import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


class CNN:
    def __init__(self, num_classes: int, num_filters: int = 8, kernel_size: int = 3,
                 hidden_dim: int = 32, seed: int = 42):
        self.num_classes = num_classes
        self.kernel_size = kernel_size
        self.num_filters = num_filters
        self.hidden_dim = hidden_dim
        self._rng = np.random.default_rng(seed)

        fan_in_conv = kernel_size * kernel_size * 3
        self.filters = (self._rng.standard_normal((num_filters, kernel_size, kernel_size, 3))
                         * np.sqrt(2.0 / fan_in_conv))
        self.conv_bias = np.zeros(num_filters)

        self.dense1_w = None  # lazy init: depends on flattened pooled size
        self.dense1_b = np.zeros(hidden_dim)
        self.dense2_w = self._rng.standard_normal((hidden_dim, num_classes)) * np.sqrt(2.0 / hidden_dim)
        self.dense2_b = np.zeros(num_classes)

    @staticmethod
    def _relu(x):
        return np.maximum(0, x)

    @staticmethod
    def softmax(x):
        shifted = x - np.max(x)
        exp = np.exp(shifted)
        return exp / np.sum(exp)

    @staticmethod
    def loss(probs, actual_idx):
        p = np.clip(probs[actual_idx], 1e-7, 1 - 1e-7)
        return -np.log(p)

    def _conv_forward(self, image):
        kh = kw = self.kernel_size
        windows = sliding_window_view(image, (kh, kw, image.shape[2]))[:, :, 0]
        out = np.tensordot(windows, self.filters, axes=([2, 3, 4], [1, 2, 3])) + self.conv_bias
        return out, windows

    @staticmethod
    def _maxpool_forward(x, size=2):
        H, W, F = x.shape
        H2, W2 = H // size, W // size
        x_trimmed = x[:H2 * size, :W2 * size, :]
        reshaped = x_trimmed.reshape(H2, size, W2, size, F)
        out = reshaped.max(axis=(1, 3))
        mask = (reshaped == out[:, None, :, None, :])
        return out, mask, x.shape

    def forward(self, image: np.ndarray):
        conv_out, windows = self._conv_forward(image)
        relu_out = self._relu(conv_out)
        pool_out, pool_mask, pre_pool_shape = self._maxpool_forward(relu_out)
        flat = pool_out.flatten()

        if self.dense1_w is None:
            fan_in = len(flat)
            self.dense1_w = self._rng.standard_normal((fan_in, self.hidden_dim)) * np.sqrt(2.0 / fan_in)

        hidden_z = flat @ self.dense1_w + self.dense1_b
        hidden_a = self._relu(hidden_z)

        out_z = hidden_a @ self.dense2_w + self.dense2_b
        probs = self.softmax(out_z)

        cache = dict(
            windows=windows, conv_out=conv_out, pool_mask=pool_mask,
            pre_pool_shape=pre_pool_shape, pool_out_shape=pool_out.shape,
            flat=flat, hidden_z=hidden_z, hidden_a=hidden_a, probs=probs,
        )
        return probs, cache

    def gradients(self, cache, actual_idx: int):
        """Gradients for one example (not applied — caller accumulates over a batch)."""
        onehot = np.zeros(self.num_classes)
        onehot[actual_idx] = 1.0
        d_out_z = cache['probs'] - onehot

        d_dense2_w = np.outer(cache['hidden_a'], d_out_z)
        d_dense2_b = d_out_z
        d_hidden_a = self.dense2_w @ d_out_z

        d_hidden_z = d_hidden_a * (cache['hidden_z'] > 0)
        d_dense1_w = np.outer(cache['flat'], d_hidden_z)
        d_dense1_b = d_hidden_z
        d_flat = d_hidden_z @ self.dense1_w.T

        d_pool_out = d_flat.reshape(cache['pool_out_shape'])

        H, W, F = cache['pre_pool_shape']
        H2, W2 = cache['pool_mask'].shape[0], cache['pool_mask'].shape[2]
        mask = cache['pool_mask']
        counts = mask.sum(axis=(1, 3), keepdims=True)
        d_relu_trimmed = (mask * d_pool_out[:, None, :, None, :]) / np.maximum(counts, 1)
        d_relu = np.zeros((H, W, F))
        d_relu[:H2 * 2, :W2 * 2, :] = d_relu_trimmed.reshape(H2 * 2, W2 * 2, F)

        d_conv_out = d_relu * (cache['conv_out'] > 0)
        d_filters = np.tensordot(d_conv_out, cache['windows'], axes=([0, 1], [0, 1]))
        d_conv_bias = d_conv_out.sum(axis=(0, 1))

        return dict(
            filters=d_filters, conv_bias=d_conv_bias,
            dense1_w=d_dense1_w, dense1_b=d_dense1_b,
            dense2_w=d_dense2_w, dense2_b=d_dense2_b,
        )

    def apply_gradients(self, grads: dict, lr: float):
        self.filters -= lr * grads['filters']
        self.conv_bias -= lr * grads['conv_bias']
        self.dense1_w -= lr * grads['dense1_w']
        self.dense1_b -= lr * grads['dense1_b']
        self.dense2_w -= lr * grads['dense2_w']
        self.dense2_b -= lr * grads['dense2_b']

    def backward(self, cache, actual_idx: int, lr=0.001):
        grads = self.gradients(cache, actual_idx)
        self.apply_gradients(grads, lr)

    def save(self, path: str):
        np.savez(path,
                  filters=self.filters, conv_bias=self.conv_bias,
                  dense1_w=self.dense1_w, dense1_b=self.dense1_b,
                  dense2_w=self.dense2_w, dense2_b=self.dense2_b,
                  num_classes=self.num_classes)

    def load(self, path: str):
        data = np.load(path)
        self.filters = data['filters']
        self.conv_bias = data['conv_bias']
        self.dense1_w = data['dense1_w']
        self.dense1_b = data['dense1_b']
        self.dense2_w = data['dense2_w']
        self.dense2_b = data['dense2_b']
        self.num_classes = int(data['num_classes'])