import os
import piexif
from tkinter import filedialog, messagebox
from tkinter import ttk
import tkinter as tk
from PIL import Image
from tkinterdnd2 import DND_FILES, TkinterDnD


def convert_png_to_webp(png_path, save_path, quality=100, lossless=False, method=6):
    """将 PNG 转 WEBP，并保留 workflow 元数据写入 EXIF。"""
    img = Image.open(png_path)
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
        root.geometry("520x420")

        self.files = []
        self.output_dir = tk.StringVar(value="")
        self.quality = tk.IntVar(value=100)
        self.lossless = tk.BooleanVar(value=False)
        self.method = tk.StringVar(value="6")

        self._build()

    def _build(self):
        pad = {"padx": 8, "pady": 4}

        # 文件选择
        frm_file = ttk.LabelFrame(self.root, text="PNG 文件列表")
        frm_file.pack(fill="x", **pad)
        self.file_list = tk.Listbox(frm_file, height=6)
        self.file_list.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self.file_list.drop_target_register(DND_FILES)
        self.file_list.dnd_bind("<<Drop>>", self._on_drop)
        btn_col = ttk.Frame(frm_file)
        btn_col.pack(side="right", padx=4)
        ttk.Button(btn_col, text="添加", command=self._add_files).pack(fill="x", pady=2)
        ttk.Button(btn_col, text="移除", command=self._remove_selected).pack(fill="x", pady=2)
        ttk.Button(btn_col, text="清空", command=self._clear_files).pack(fill="x", pady=2)

        # 输出目录
        frm_out = ttk.LabelFrame(self.root, text="输出目录")
        frm_out.pack(fill="x", **pad)
        ttk.Entry(frm_out, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=4, pady=4)
        ttk.Button(frm_out, text="选择", command=self._choose_output).pack(side="right", padx=4)

        # 参数
        frm_opt = ttk.LabelFrame(self.root, text="转换参数")
        frm_opt.pack(fill="x", **pad)
        ttk.Label(frm_opt, text="quality").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        ttk.Scale(frm_opt, from_=1, to=100, variable=self.quality, command=self._on_quality_change, orient="horizontal").grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        self.quality_label = ttk.Label(frm_opt, text="100")
        self.quality_label.grid(row=0, column=2, padx=4)
        ttk.Label(frm_opt, text="lossless").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        ttk.Checkbutton(frm_opt, variable=self.lossless).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(frm_opt, text="method").grid(row=2, column=0, sticky="e", padx=4, pady=2)
        ttk.Combobox(frm_opt, textvariable=self.method, values=["0", "1", "2", "3", "4", "5", "6"], state="readonly", width=4).grid(row=2, column=1, sticky="w", padx=4)
        frm_opt.columnconfigure(1, weight=1)

        # 操作
        frm_act = ttk.Frame(self.root)
        frm_act.pack(fill="x", **pad)
        ttk.Button(frm_act, text="开始转换", command=self._convert).pack(side="left", padx=4)

        # 状态
        self.status = ttk.Label(self.root, text="就绪")
        self.status.pack(fill="x", **pad)

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

    def _convert(self):
        if not self.files:
            messagebox.showwarning("提示", "请先添加 PNG 文件")
            return
        out_dir = self.output_dir.get() or os.path.dirname(self.files[0])
        os.makedirs(out_dir, exist_ok=True)
        ok, fail = 0, 0
        quality = self.quality.get()
        lossless = self.lossless.get()
        method = int(self.method.get())
        for png_path in self.files:
            save_path = os.path.join(out_dir, os.path.splitext(os.path.basename(png_path))[0] + ".webp")
            try:
                convert_png_to_webp(png_path, save_path, quality, lossless, method)
                ok += 1
            except Exception as e:
                fail += 1
                self.status.config(text=f"失败: {os.path.basename(png_path)} - {e}")
        self.status.config(text=f"完成: 成功 {ok} 个，失败 {fail} 个")
        messagebox.showinfo("完成", f"成功 {ok} 个，失败 {fail} 个")


def main():
    root = TkinterDnD.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()