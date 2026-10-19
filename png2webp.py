import os
import queue
import threading
import piexif
from tkinter import filedialog, messagebox
from tkinter import ttk
import tkinter as tk
from PIL import Image
from tkinterdnd2 import DND_FILES, TkinterDnD


def convert_png_to_webp(png_path, save_path, quality=100, lossless=False, method=6):
    """将 PNG 转 WEBP，并保留 workflow 元数据写入 EXIF。"""
    with Image.open(png_path) as img:
        workflow = img.info.get("workflow")
        exif_bytes = None
        if workflow:
            exif_dict = {"0th": {piexif.ImageIFD.ImageDescription: "Workflow:" + workflow}}
            exif_bytes = piexif.dump(exif_dict)
        save_kwargs = {"quality": quality, "lossless": lossless, "method": method}
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes
        img.save(save_path, "WEBP", **save_kwargs)


class App:
    def __init__(self, root):
        self.root = root
        root.title("PNG 转 WEBP（保留 workflow）")
        self.width = 520
        root.geometry(f"{self.width}x460")

        self.files = []
        # 后台线程通过队列回传进度，主线程用 after 轮询刷新界面
        self.queue = queue.Queue()
        self.busy = False
        self.output_dir = tk.StringVar(value="D:/desktop/webp")
        self.quality = tk.IntVar(value=100)
        self.lossless = tk.BooleanVar(value=False)
        self.method = tk.StringVar(value="6")

        self._build()

    def _build(self):
        pad = self.pad = {"padx": 8, "pady": 4}

        # 文件选择
        frm_file = ttk.LabelFrame(self.root, text="PNG 文件列表")
        frm_file.pack(fill="x", **pad)
        self.file_list = tk.Listbox(frm_file, height=6)
        self.file_list.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self.file_list.drop_target_register(DND_FILES)
        self.file_list.dnd_bind("<<Drop>>", self._on_drop)
        btn_col = ttk.Frame(frm_file)
        btn_col.pack(side="right", padx=4)
        self.btn_add = ttk.Button(btn_col, text="添加", command=self._add_files)
        self.btn_add.pack(fill="x", pady=2)
        self.btn_remove = ttk.Button(btn_col, text="移除", command=self._remove_selected)
        self.btn_remove.pack(fill="x", pady=2)
        self.btn_clear = ttk.Button(btn_col, text="清空", command=self._clear_files)
        self.btn_clear.pack(fill="x", pady=2)
        self.file_scroll = ttk.Scrollbar(frm_file, orient="vertical", command=self.file_list.yview)
        self.file_scroll.pack(side="right", fill="y", pady=4)
        self.file_list.config(yscrollcommand=self.file_scroll.set)

        # 输出目录
        frm_out = ttk.LabelFrame(self.root, text="输出目录")
        frm_out.pack(fill="x", **pad)
        ttk.Entry(frm_out, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=4, pady=4)
        self.btn_output = ttk.Button(frm_out, text="选择", command=self._choose_output)
        self.btn_output.pack(side="right", padx=4)

        # 参数（默认收起，标题显示当前参数摘要）
        self.opt_expanded = False
        self.opt_header = ttk.Button(self.root, style="Toolbutton", command=self._toggle_opt)
        self.opt_header.pack(fill="x", **pad)
        self.frm_opt = ttk.LabelFrame(self.root)
        ttk.Label(self.frm_opt, text="quality").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        ttk.Scale(self.frm_opt, from_=1, to=100, variable=self.quality, command=self._on_quality_change, orient="horizontal").grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        self.quality_label = ttk.Label(self.frm_opt, text="100")
        self.quality_label.grid(row=0, column=2, padx=4)
        ttk.Label(self.frm_opt, text="lossless").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        ttk.Checkbutton(self.frm_opt, variable=self.lossless, command=self._update_opt_header).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(self.frm_opt, text="method").grid(row=2, column=0, sticky="e", padx=4, pady=2)
        cb_method = ttk.Combobox(self.frm_opt, textvariable=self.method, values=["0", "1", "2", "3", "4", "5", "6"], state="readonly", width=4)
        cb_method.grid(row=2, column=1, sticky="w", padx=4)
        cb_method.bind("<<ComboboxSelected>>", self._on_method_change)
        self.frm_opt.columnconfigure(1, weight=1)
        self._update_opt_header()

        # 操作
        frm_act = ttk.Frame(self.root)
        frm_act.pack(fill="x", **pad)
        self.btn_start = ttk.Button(frm_act, text="开始转换", command=self._convert)
        self.btn_start.pack(side="left", padx=4)

        # 进度与状态
        self.progress_var = tk.IntVar(value=0)
        self.progress = ttk.Progressbar(self.root, variable=self.progress_var, maximum=1)
        self.progress.pack(fill="x", **pad)
        self.status = ttk.Label(self.root, text="就绪")
        self.status.pack(fill="x", **pad)

        self._fit_height()

    def _add_files(self):
        paths = filedialog.askopenfilenames(filetypes=[("PNG 图片", "*.png")])
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.file_list.insert("end", os.path.basename(p))

    def _on_drop(self, event):
        # tkinterdnd2 用花括号包裹含空格的路径，需按此解析
        paths = self.root.tk.splitlist(event.data)
        for p in filter(lambda x: x.lower().endswith(".png"), paths):
            if p not in self.files:
                self.files.append(p)
                self.file_list.insert("end", os.path.basename(p))

    def _remove_selected(self):
        for idx in reversed(self.file_list.curselection()):
            self.file_list.delete(idx)
            del self.files[idx]

    def _clear_files(self):
        self.files.clear()
        self.file_list.delete(0, "end")

    def _choose_output(self):
        d = filedialog.askdirectory()
        if d:
            self.output_dir.set(d)

    def _on_quality_change(self, value):
        # Scale 回调传入浮点，取整后同时更新 IntVar 与标签显示
        rounded = int(round(float(value)))
        self.quality.set(rounded)
        self.quality_label.config(text=str(rounded))
        self._update_opt_header()

    def _on_method_change(self, event):
        self._update_opt_header()

    def _update_opt_header(self):
        arrow = "▾" if self.opt_expanded else "▸"
        if self.lossless.get():
            # 无损模式下 quality 不生效，摘要里不显示
            summary = f"无损 · method {self.method.get()}"
        else:
            summary = f"质量 {self.quality.get()} · 有损 · method {self.method.get()}"
        self.opt_header.config(text=f"{arrow} 转换参数（{summary}）")

    def _toggle_opt(self):
        self.opt_expanded = not self.opt_expanded
        if self.opt_expanded:
            # 必须指定锚点，否则重新 pack 会落到窗口底部
            self.frm_opt.pack(after=self.opt_header, fill="x", **self.pad)
        else:
            self.frm_opt.pack_forget()
        self._update_opt_header()
        self._fit_height()

    def _fit_height(self):
        """按当前内容高度调整窗口，展开/收起参数区时不留下空白。"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        if width <= 1:
            # 窗口尚未映射时取不到实际宽度，退回初始宽度
            width = self.width
        self.root.geometry(f"{width}x{self.root.winfo_reqheight()}")

    def _convert(self):
        if self.busy:
            return
        if not self.files:
            messagebox.showwarning("提示", "请先添加 PNG 文件")
            return
        out_dir = self.output_dir.get() or os.path.dirname(self.files[0])
        os.makedirs(out_dir, exist_ok=True)
        quality = self.quality.get()
        lossless = self.lossless.get()
        method = int(self.method.get())
        files = list(self.files)  # 快照，转换期间列表变化不影响本次任务

        self.busy = True
        self._set_controls_enabled(False)
        self.progress.config(maximum=len(files))
        self.progress_var.set(0)
        self.status.config(text=f"正在转换 0/{len(files)}")

        threading.Thread(
            target=self._worker,
            args=(files, out_dir, quality, lossless, method),
            daemon=True,
        ).start()
        self.root.after(100, self._poll_queue)

    def _set_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for widget in (self.btn_add, self.btn_remove, self.btn_clear, self.btn_output, self.btn_start):
            widget.config(state=state)

    def _worker(self, files, out_dir, quality, lossless, method):
        """后台线程：只做转换，结果全部经队列交给主线程渲染。"""
        ok, fail = 0, 0
        failures = []
        total = len(files)
        for i, png_path in enumerate(files, start=1):
            name = os.path.basename(png_path)
            save_path = os.path.join(out_dir, os.path.splitext(name)[0] + ".webp")
            try:
                convert_png_to_webp(png_path, save_path, quality, lossless, method)
                ok += 1
                self.queue.put(("progress", i, total, name, None))
            except Exception as e:
                fail += 1
                failures.append((name, str(e)))
                self.queue.put(("progress", i, total, name, str(e)))
        self.queue.put(("done", ok, fail, failures))

    def _poll_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg[0] == "progress":
                    _, i, total, name, err = msg
                    self.progress_var.set(i)
                    if err:
                        self.status.config(text=f"失败 {i}/{total}: {name} - {err}")
                    else:
                        self.status.config(text=f"正在转换 {i}/{total}: {name}")
                else:
                    self._finish(*msg[1:])
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _finish(self, ok, fail, failures):
        self.busy = False
        self._set_controls_enabled(True)
        self.status.config(text=f"完成: 成功 {ok} 个，失败 {fail} 个")
        detail = f"成功 {ok} 个，失败 {fail} 个"
        if failures:
            detail += "\n\n失败明细：\n" + "\n".join(f"- {name}: {err}" for name, err in failures)
        messagebox.showinfo("完成", detail)


def main():
    root = TkinterDnD.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()