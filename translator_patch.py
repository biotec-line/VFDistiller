import tkinter as tk
from tkinter import ttk

def patch_widgets(translator):
    def wrap_factory(widget_cls):
        class Wrapped(widget_cls):
            def __init__(self, master=None, **kw):
                if "text" in kw:
                    kw["text"] = translator.t(kw["text"])
                super().__init__(master, **kw)
        return Wrapped

    # Patch anwenden
    tk.Label = wrap_factory(tk.Label)
    ttk.Label = wrap_factory(ttk.Label)
    ttk.Button = wrap_factory(ttk.Button)
    ttk.Checkbutton = wrap_factory(ttk.Checkbutton)
    ttk.Radiobutton = wrap_factory(ttk.Radiobutton)