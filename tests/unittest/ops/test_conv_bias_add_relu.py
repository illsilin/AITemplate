#  Copyright (c) Meta Platforms, Inc. and affiliates.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import unittest

import torch
from aitemplate.compiler import compile_model, ops
from aitemplate.frontend import IntImm, Tensor
from aitemplate.testing import detect_target


class ConvBiasReluAddTestCase(unittest.TestCase):
    def _test_fp16(self, batch=4, copy_op=False):
        target = detect_target()
        CO, HH, WW, CI = 256, 28, 28, 128
        X = Tensor(
            shape=[IntImm(batch), HH, WW, CI],
            dtype="float16",
            name="input_0",
            is_input=True,
        )

        W = Tensor(shape=[CO, 3, 3, CI], dtype="float16", name="input_1", is_input=True)
        B = Tensor(shape=[CO], dtype="float16", name="input_2", is_input=True)
        R = Tensor(
            shape=[IntImm(batch), HH, WW, CO],
            dtype="float16",
            name="input_3",
            is_input=True,
        )
        OP = ops.conv2d_bias_add_relu(stride=1, pad=1, dilate=1)
        if copy_op:
            OP = ops.conv2d_bias_add_relu(**OP._get_op_attributes())
        Y = OP(X, W, B, R)
        Y._attrs["name"] = "output_0"
        Y._attrs["is_output"] = True
        module = compile_model(Y, target, "./tmp", "conv2d_bias_add_relu")

        X_pt = torch.randn(batch, CI, HH, WW).cuda().half()
        W_pt = torch.randn(CO, CI, 3, 3).cuda().half()
        B_pt = torch.randn(1, CO, 1, 1).cuda().half()
        R_pt = torch.randn(batch, CO, HH, WW).cuda().half()
        Y_pt = torch.nn.functional.conv2d(X_pt, W_pt, padding=1)
        Y_pt = Y_pt + B_pt + R_pt
        Y_pt = torch.nn.functional.relu(Y_pt)

        x = X_pt.permute((0, 2, 3, 1)).contiguous()
        w = W_pt.permute((0, 2, 3, 1)).contiguous()
        r = R_pt.permute((0, 2, 3, 1)).contiguous()
        inputs = {"input_0": x, "input_1": w, "input_2": B_pt.squeeze(), "input_3": r}
        y = torch.empty([batch, HH, WW, CO]).cuda().half()
        module.run_with_tensors(inputs, [y])
        y_transpose = y.permute(0, 3, 1, 2)
        self.assertTrue(torch.allclose(Y_pt, y_transpose, atol=1e-2, rtol=1e-2))

    def test_fp16(self):
        self._test_fp16()
        self._test_fp16(copy_op=True)

    def test_fp16(self):
        self._test_fp16()
        self._test_fp16(copy_op=True)


if __name__ == "__main__":
    torch.manual_seed(0)
    unittest.main()
