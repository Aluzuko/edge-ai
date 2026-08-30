import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


class CNN:
   
    def __init__(self, num_classes: int, num_filters: int = 8, kernel_size: int = 3,
                 hidden_dim: int = 32, seed: int = 42, dropout_rate: float = 0.3,
                 num_filters2: int | None = None):
        self.num_classes = num_classes
        self.kernel_size = kernel_size
        self.num_filters = num_filters
        self.num_filters2 = num_filters2 if num_filters2 is not None else num_filters * 2
        self.hidden_dim = hidden_dim
        self.dropout_rate = dropout_rate
        self._rng = np.random.default_rng(seed)

        fan_in_conv = kernel_size * kernel_size * 3
        self.filters = (
            self._rng.standard_normal((num_filters, kernel_size, kernel_size, 3)).astype(np.float32)
            * np.sqrt(2.0 / fan_in_conv)
        ).astype(np.float32)
        self.conv_bias = np.zeros(num_filters, dtype=np.float32)

        fan_in_conv2 = kernel_size * kernel_size * num_filters
        self.filters2 = (
            self._rng.standard_normal((self.num_filters2, kernel_size, kernel_size, num_filters)).astype(np.float32)
            * np.sqrt(2.0 / fan_in_conv2)
        ).astype(np.float32)
        self.conv2_bias = np.zeros(self.num_filters2, dtype=np.float32)

        self.dense1_w = None
        self.dense1_b = np.zeros(hidden_dim, dtype=np.float32)
        self.dense2_w = (
            self._rng.standard_normal((hidden_dim, num_classes)).astype(np.float32)
            * np.sqrt(2.0 / hidden_dim)
        ).astype(np.float32)
        self.dense2_b = np.zeros(num_classes, dtype=np.float32)

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

    @staticmethod
    def _conv_forward_generic(x, filters, bias):
        kh, kw = filters.shape[1], filters.shape[2]
        windows = sliding_window_view(x, (kh, kw, x.shape[2]))[:, :, 0]
        out = np.tensordot(windows, filters, axes=([2, 3, 4], [1, 2, 3])) + bias
        return out, windows

    @staticmethod
    def _conv_backward_generic(d_out, windows, filters, input_shape):
       
        d_filters = np.tensordot(d_out, windows, axes=([0, 1], [0, 1]))
        d_bias = d_out.sum(axis=(0, 1))

        kh, kw = filters.shape[1], filters.shape[2]
        # (H_out, W_out, kh, kw, C_in)
        d_windows = np.tensordot(d_out, filters, axes=([2], [0]))
        d_input = np.zeros(input_shape, dtype=np.float32)
        H_out, W_out = d_out.shape[0], d_out.shape[1]
        for di in range(kh):
            for dj in range(kw):
                d_input[di:di + H_out, dj:dj + W_out, :] += d_windows[:, :, di, dj, :]
        return d_filters, d_bias, d_input

    @staticmethod
    def _maxpool_forward(x, size=2):
        H, W, F = x.shape
        H2, W2 = H // size, W // size
        x_trimmed = x[:H2 * size, :W2 * size, :]
        reshaped = x_trimmed.reshape(H2, size, W2, size, F)
        out = reshaped.max(axis=(1, 3))
        mask = (reshaped == out[:, None, :, None, :])
        return out, mask, x.shape

    @staticmethod
    def _maxpool_backward(d_pool_out, mask, pre_pool_shape, size=2):
        H, W, F = pre_pool_shape
        H2, W2 = mask.shape[0], mask.shape[2]
        counts = mask.sum(axis=(1, 3), keepdims=True)
        d_trimmed = (mask * d_pool_out[:, None, :, None, :]) / np.maximum(counts, 1)
        d_full = np.zeros((H, W, F), dtype=np.float32)
        d_full[:H2 * size, :W2 * size, :] = d_trimmed.reshape(H2 * size, W2 * size, F)
        return d_full

    def forward(self, image: np.ndarray, training: bool = False):
        conv_out, windows = self._conv_forward_generic(image, self.filters, self.conv_bias)
        relu_out = self._relu(conv_out)
        pool_out, pool_mask, pre_pool_shape = self._maxpool_forward(relu_out)

        conv2_out, windows2 = self._conv_forward_generic(pool_out, self.filters2, self.conv2_bias)
        relu2_out = self._relu(conv2_out)
        pool2_out, pool2_mask, pre_pool2_shape = self._maxpool_forward(relu2_out)

        flat = pool2_out.astype(np.float32).flatten()

        if self.dense1_w is None:
            fan_in = len(flat)
            self.dense1_w = (
                self._rng.standard_normal((fan_in, self.hidden_dim)).astype(np.float32)
                * np.sqrt(2.0 / fan_in)
            ).astype(np.float32)

        hidden_z = flat @ self.dense1_w + self.dense1_b
        hidden_a = self._relu(hidden_z)

        # Inverted dropout: only active during training, and rescaled so
        # eval-time forward passes (training=False) need no adjustment.
        if training and self.dropout_rate > 0:
            keep_prob = 1.0 - self.dropout_rate
            dropout_mask = (
                self._rng.random(hidden_a.shape) < keep_prob
            ).astype(np.float32) / keep_prob
        else:
            dropout_mask = np.ones_like(hidden_a)
        hidden_a_used = hidden_a * dropout_mask

        out_z = hidden_a_used @ self.dense2_w + self.dense2_b
        probs = self.softmax(out_z)

        cache = dict(
            windows=windows, conv_out=conv_out, pool_mask=pool_mask,
            pre_pool_shape=pre_pool_shape, pool_out=pool_out,
            windows2=windows2, conv2_out=conv2_out, pool2_mask=pool2_mask,
            pre_pool2_shape=pre_pool2_shape, pool2_out_shape=pool2_out.shape,
            flat=flat, hidden_z=hidden_z, hidden_a=hidden_a_used,
            dropout_mask=dropout_mask, probs=probs,
        )
        return probs, cache

    def gradients(self, cache, actual_idx: int):
        onehot = np.zeros(self.num_classes, dtype=np.float32)
        onehot[actual_idx] = 1.0
        d_out_z = cache['probs'] - onehot

        d_dense2_w = np.outer(cache['hidden_a'], d_out_z).astype(np.float32)
        d_dense2_b = d_out_z.astype(np.float32)
        d_hidden_a = self.dense2_w @ d_out_z
        d_hidden_a = d_hidden_a * cache['dropout_mask']  # backprop through dropout

        d_hidden_z = d_hidden_a * (cache['hidden_z'] > 0)
        d_dense1_w = np.outer(cache['flat'], d_hidden_z).astype(np.float32)
        d_dense1_b = d_hidden_z.astype(np.float32)
        d_flat = d_hidden_z @ self.dense1_w.T

        # --- block 2 ---
        d_pool2_out = d_flat.reshape(cache['pool2_out_shape'])
        d_relu2 = self._maxpool_backward(d_pool2_out, cache['pool2_mask'], cache['pre_pool2_shape'])
        d_conv2_out = d_relu2 * (cache['conv2_out'] > 0)
        d_filters2, d_conv2_bias, d_pool_out = self._conv_backward_generic(
            d_conv2_out, cache['windows2'], self.filters2, cache['pool_out'].shape
        )

        # --- block 1 ---
        d_relu = self._maxpool_backward(d_pool_out, cache['pool_mask'], cache['pre_pool_shape'])
        d_conv_out = d_relu * (cache['conv_out'] > 0)
        d_filters = np.tensordot(d_conv_out, cache['windows'], axes=([0, 1], [0, 1]))
        d_conv_bias = d_conv_out.sum(axis=(0, 1))

        return dict(
            filters=d_filters, conv_bias=d_conv_bias,
            filters2=d_filters2, conv2_bias=d_conv2_bias,
            dense1_w=d_dense1_w, dense1_b=d_dense1_b,
            dense2_w=d_dense2_w, dense2_b=d_dense2_b,
        )

    def apply_gradients(self, grads: dict, lr: float, weight_decay: float = 0.0):
        # L2 weight decay on weight tensors only (not biases).
        self.filters -= lr * (grads['filters'] + weight_decay * self.filters)
        self.conv_bias -= lr * grads['conv_bias']
        self.filters2 -= lr * (grads['filters2'] + weight_decay * self.filters2)
        self.conv2_bias -= lr * grads['conv2_bias']
        self.dense1_w -= lr * (grads['dense1_w'] + weight_decay * self.dense1_w)
        self.dense1_b -= lr * grads['dense1_b']
        self.dense2_w -= lr * (grads['dense2_w'] + weight_decay * self.dense2_w)
        self.dense2_b -= lr * grads['dense2_b']

    def backward(self, cache, actual_idx: int, lr=0.001, weight_decay: float = 0.0):
        grads = self.gradients(cache, actual_idx)
        self.apply_gradients(grads, lr, weight_decay=weight_decay)

    def save(self, path: str):
        np.savez(path,
                  filters=self.filters, conv_bias=self.conv_bias,
                  filters2=self.filters2, conv2_bias=self.conv2_bias,
                  dense1_w=self.dense1_w, dense1_b=self.dense1_b,
                  dense2_w=self.dense2_w, dense2_b=self.dense2_b,
                  num_classes=self.num_classes)

    def load(self, path: str):
        data = np.load(path)
        if 'filters2' not in data:
            raise ValueError(
                f"{path} is a single-conv-block checkpoint from the older CNN. "
                "The architecture now has two conv blocks, so old checkpoints "
                "can't be loaded -- retrain and use the new best.npz."
            )
        self.filters = data['filters']
        self.conv_bias = data['conv_bias']
        self.filters2 = data['filters2']
        self.conv2_bias = data['conv2_bias']
        self.dense1_w = data['dense1_w']
        self.dense1_b = data['dense1_b']
        self.dense2_w = data['dense2_w']
        self.dense2_b = data['dense2_b']
        self.num_classes = int(data['num_classes'])
        self.num_filters = self.filters.shape[0]
        self.num_filters2 = self.filters2.shape[0]
