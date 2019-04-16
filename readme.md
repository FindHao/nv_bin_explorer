# NV Bin Explorer

It's simple tool to explore CUDA binary file in CC7.0+.

The input file is a cubin file where you can get it by `-keep` params when compile your CUDA C program.

`com_lib.kernel_section_start_offset` is the kernel section entrance. Use `readelf -a ./test.cubin` to get your cubin file's kernel section start offset.

execute:

```bash
python3 ./opcoder.py
```