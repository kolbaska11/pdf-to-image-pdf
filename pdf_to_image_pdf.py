import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class PDFRasterizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF → PDF (страницы-картинки)")
        self.root.geometry("620x390")
        self.root.minsize(560, 350)

        self.files = []
        self.output_dir = tk.StringVar(value="")
        self.dpi = tk.IntVar(value=200)
        self.status = tk.StringVar(value="Добавьте один или несколько PDF-файлов.")
        self.busy = False

        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="Преобразование PDF в PDF с изображениями",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")

        file_row = ttk.Frame(main)
        file_row.pack(fill="x", pady=(14, 6))
        ttk.Button(file_row, text="Выбрать PDF-файлы…", command=self.choose_files).pack(side="left")
        self.file_label = ttk.Label(file_row, text="Файлы не выбраны")
        self.file_label.pack(side="left", padx=10)

        out_row = ttk.Frame(main)
        out_row.pack(fill="x", pady=6)
        ttk.Label(out_row, text="Папка результата:").pack(side="left")
        ttk.Entry(out_row, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(out_row, text="Обзор…", command=self.choose_output_dir).pack(side="right")

        dpi_row = ttk.Frame(main)
        dpi_row.pack(fill="x", pady=(12, 4))
        ttk.Label(dpi_row, text="Качество (DPI):").pack(side="left")
        self.dpi_combo = ttk.Combobox(
            dpi_row, textvariable=self.dpi, values=(100, 150, 200),
            state="readonly", width=8
        )
        self.dpi_combo.pack(side="left", padx=8)
        ttk.Label(dpi_row, text="200 DPI — рекомендуется для мелкого текста").pack(side="left")

        self.progress = ttk.Progressbar(main, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(18, 8))
        ttk.Label(main, textvariable=self.status, wraplength=570).pack(anchor="w")

        self.start_button = ttk.Button(main, text="Преобразовать", command=self.start)
        self.start_button.pack(anchor="e", pady=(18, 0))

        if fitz is None:
            self.status.set("Не установлена библиотека PyMuPDF. Закройте программу и выполните: pip install pymupdf")
            self.start_button.configure(state="disabled")

    def choose_files(self):
        if self.busy:
            return
        selected = filedialog.askopenfilenames(
            title="Выберите PDF-файлы",
            filetypes=[("PDF-файлы", "*.pdf")]
        )
        if selected:
            self.files = list(selected)
            self.file_label.config(text=f"Выбрано файлов: {len(self.files)}")
            if not self.output_dir.get():
                self.output_dir.set(os.path.dirname(self.files[0]))
            self.status.set("Готово к преобразованию.")

    def choose_output_dir(self):
        folder = filedialog.askdirectory(title="Куда сохранить готовые PDF")
        if folder:
            self.output_dir.set(folder)

    def start(self):
        if self.busy:
            return
        if not self.files:
            messagebox.showwarning("Нет файлов", "Сначала выберите хотя бы один PDF-файл.")
            return
        out_dir = self.output_dir.get().strip()
        if not out_dir or not os.path.isdir(out_dir):
            messagebox.showwarning("Папка не выбрана", "Выберите существующую папку для результатов.")
            return

        self.busy = True
        self.start_button.configure(state="disabled")
        self.progress["value"] = 0
        threading.Thread(target=self.process_files, args=(out_dir, int(self.dpi.get())), daemon=True).start()

    def set_status(self, text):
        self.root.after(0, self.status.set, text)

    def set_progress(self, value):
        self.root.after(0, lambda: self.progress.configure(value=value))

    def finish(self, message, errors):
        def done():
            self.busy = False
            self.start_button.configure(state="normal")
            if errors:
                messagebox.showwarning("Завершено с ошибками", message)
            else:
                messagebox.showinfo("Готово", message)
        self.root.after(0, done)

    def process_files(self, out_dir, dpi):
        completed = 0
        errors = []
        total = len(self.files)

        for file_index, source_path in enumerate(self.files, start=1):
            base = os.path.splitext(os.path.basename(source_path))[0]
            output_path = os.path.join(out_dir, f"{base}_raster.pdf")

            # Preserve previous results and same-named files from different folders.
            number = 2
            while os.path.exists(output_path):
                output_path = os.path.join(out_dir, f"{base}_raster_{number}.pdf")
                number += 1

            try:
                self.set_status(f"Файл {file_index}/{total}: {os.path.basename(source_path)}")
                with fitz.open(source_path) as src:
                    if src.needs_pass:
                        raise RuntimeError("PDF защищён паролем; сначала снимите защиту.")
                    result = fitz.open()
                    try:
                        scale = dpi / 72.0
                        page_count = len(src)
                        for page_index, page in enumerate(src):
                            pix = page.get_pixmap(
                                matrix=fitz.Matrix(scale, scale),
                                colorspace=fitz.csRGB,
                                alpha=False
                            )
                            image_bytes = pix.tobytes("png")

                            # Keep the exact original page rectangle and page dimensions.
                            new_page = result.new_page(
                                width=page.rect.width,
                                height=page.rect.height
                            )
                            new_page.insert_image(new_page.rect, stream=image_bytes)

                            overall = ((file_index - 1) + (page_index + 1) / max(page_count, 1)) / total * 100
                            self.set_progress(overall)

                        result.save(output_path, deflate=True, garbage=3)
                    finally:
                        result.close()
                completed += 1
            except Exception as exc:
                errors.append(f"{os.path.basename(source_path)}: {exc}")

        self.set_progress(100)
        if errors:
            summary = f"Успешно: {completed} из {total}.\n\nОшибки:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                summary += f"\n…и ещё ошибок: {len(errors) - 10}"
            self.finish(summary, errors)
        else:
            self.set_status(f"Готово. Обработано файлов: {completed}.")
            self.finish(
                f"Готово! Обработано файлов: {completed}.\nРазрешение: {dpi} DPI.\nПапка: {out_dir}",
                errors
            )


def main():
    root = tk.Tk()
    PDFRasterizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
