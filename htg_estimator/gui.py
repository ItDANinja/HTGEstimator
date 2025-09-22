"""Graphical user interface for HTG Estimator."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

try:  # pragma: no cover - optional dependency handled at runtime
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
except Exception:  # pragma: no cover - defer failure until GUI launched
    tk = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    filedialog = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]
    simpledialog = None  # type: ignore[assignment]

from .estimator import Estimator
from .formatter import format_estimate
from .market_data import list_available_categories
from .models import ProjectInput


@dataclass(slots=True)
class LaborPhaseData:
    """Container for a single labor phase entry."""

    phase: str
    description: str
    hours_low: float
    hours_high: float

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "description": self.description,
            "hours": {"low": self.hours_low, "high": self.hours_high},
        }


@dataclass(slots=True)
class MaterialData:
    """Container for a single material line item."""

    name: str
    quantity: float
    unit_cost_low: float
    unit_cost_high: Optional[float] = None
    unit: Optional[str] = None
    waste_factor: Optional[float] = None
    price_drift: Optional[float] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "name": self.name,
            "quantity": self.quantity,
            "unit_cost_low": self.unit_cost_low,
        }
        if self.unit_cost_high is not None:
            data["unit_cost_high"] = self.unit_cost_high
        if self.unit:
            data["unit"] = self.unit
        if self.waste_factor is not None:
            data["waste_factor"] = self.waste_factor
        if self.price_drift is not None:
            data["price_drift"] = self.price_drift
        if self.notes:
            data["notes"] = self.notes
        return data


@dataclass(slots=True)
class AttachmentData:
    """Container describing a client attachment."""

    path: str
    kind: str
    description: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"path": self.path, "kind": self.kind}
        if self.description:
            data["description"] = self.description
        return data


@dataclass(slots=True)
class ServiceData:
    """Editable representation of a service scope."""

    name: str
    service_type: str
    breakdown: List[LaborPhaseData] = field(default_factory=list)
    materials: List[MaterialData] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    stage_returns: int = 0
    permit_required: bool = False
    notes: Optional[str] = None
    market_rate_low: Optional[float] = None
    market_rate_high: Optional[float] = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "name": self.name,
            "service_type": self.service_type,
            "breakdown": [phase.to_dict() for phase in self.breakdown],
            "materials": [material.to_dict() for material in self.materials],
            "assumptions": list(self.assumptions),
            "exclusions": list(self.exclusions),
        }
        if self.stage_returns:
            data["stage_returns"] = self.stage_returns
        if self.permit_required:
            data["permit_required"] = self.permit_required
        if self.notes:
            data["notes"] = self.notes
        if self.market_rate_low is not None or self.market_rate_high is not None:
            low = self.market_rate_low if self.market_rate_low is not None else self.market_rate_high
            high = self.market_rate_high if self.market_rate_high is not None else self.market_rate_low
            if low is not None:
                data["market_rate_override"] = {"low": low, "high": high if high is not None else low}
        return data


class EstimatorGUI:
    """Main GUI application."""

    def __init__(self) -> None:
        if tk is None or ttk is None:  # pragma: no cover - GUI requires tkinter
            raise RuntimeError(
                "tkinter is required to launch the HTG Estimator GUI. "
                "Install a Python distribution with tkinter support (python3-tk)."
            )

        self.root = tk.Tk()
        self.root.title("HTG Estimator — Professional Construction Estimate Builder")
        self.root.geometry("1080x760")
        self.root.minsize(960, 640)

        self.client_name_var = tk.StringVar()
        self.project_address_var = tk.StringVar()

        self.site_conditions: List[str] = []
        self.clarifying_questions: List[str] = []
        self.attachments: List[AttachmentData] = []
        self.services: List[ServiceData] = []

        self._available_service_types = sorted(list_available_categories().keys())

        self._last_estimate_text: Optional[str] = None
        self._last_request_payload: Optional[dict[str, object]] = None

        self._build_ui()

    def run(self) -> None:
        """Start the Tkinter main loop."""

        self.root.mainloop()

    # -- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:  # pragma: no cover - theme availability depends on host
            pass
        style.configure("Heading.TLabel", font=("Segoe UI", 12, "bold"))

        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.project_tab = ttk.Frame(notebook, padding=16)
        notebook.add(self.project_tab, text="Project Info")

        self.services_tab = ttk.Frame(notebook, padding=16)
        notebook.add(self.services_tab, text="Services")

        self.attachments_tab = ttk.Frame(notebook, padding=16)
        notebook.add(self.attachments_tab, text="Attachments & Conditions")

        self.preview_tab = ttk.Frame(notebook, padding=16)
        notebook.add(self.preview_tab, text="Estimate Preview")

        self._build_project_tab()
        self._build_services_tab()
        self._build_attachments_tab()
        self._build_preview_tab()

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(12, 0))

        generate_btn = ttk.Button(action_frame, text="Generate Estimate", command=self._generate_estimate)
        generate_btn.pack(side=tk.LEFT)

        export_btn = ttk.Button(action_frame, text="Export Request JSON", command=self._export_request)
        export_btn.pack(side=tk.LEFT, padx=(12, 0))

        close_btn = ttk.Button(action_frame, text="Close", command=self.root.destroy)
        close_btn.pack(side=tk.RIGHT)

    def _build_project_tab(self) -> None:
        ttk.Label(self.project_tab, text="Client Details", style="Heading.TLabel").grid(row=0, column=0, sticky=tk.W)

        ttk.Label(self.project_tab, text="Client Name:").grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        client_entry = ttk.Entry(self.project_tab, textvariable=self.client_name_var, width=40)
        client_entry.grid(row=1, column=1, sticky=tk.W, pady=(6, 0))

        ttk.Label(self.project_tab, text="Project Address:").grid(row=2, column=0, sticky=tk.W, pady=(6, 0))
        address_entry = ttk.Entry(self.project_tab, textvariable=self.project_address_var, width=60)
        address_entry.grid(row=2, column=1, sticky=tk.W, pady=(6, 0))

        ttk.Label(self.project_tab, text="Request Summary:").grid(row=3, column=0, sticky=tk.NW, pady=(6, 0))
        self.request_summary = tk.Text(self.project_tab, width=70, height=5)
        self.request_summary.grid(row=3, column=1, sticky=tk.EW, pady=(6, 0))

        ttk.Label(self.project_tab, text="Site Conditions", style="Heading.TLabel").grid(
            row=4, column=0, sticky=tk.W, pady=(16, 0)
        )

        self.site_conditions_listbox = tk.Listbox(self.project_tab, height=6)
        self.site_conditions_listbox.grid(row=5, column=0, columnspan=2, sticky=tk.EW)

        site_btn_frame = ttk.Frame(self.project_tab)
        site_btn_frame.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))
        ttk.Button(site_btn_frame, text="Add", command=self._add_site_condition).pack(side=tk.LEFT)
        ttk.Button(site_btn_frame, text="Edit", command=self._edit_site_condition).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(site_btn_frame, text="Remove", command=self._remove_site_condition).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(self.project_tab, text="Clarifying Questions", style="Heading.TLabel").grid(
            row=7, column=0, sticky=tk.W, pady=(16, 0)
        )

        self.questions_listbox = tk.Listbox(self.project_tab, height=6)
        self.questions_listbox.grid(row=8, column=0, columnspan=2, sticky=tk.EW)

        questions_btn_frame = ttk.Frame(self.project_tab)
        questions_btn_frame.grid(row=9, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))
        ttk.Button(questions_btn_frame, text="Add", command=self._add_question).pack(side=tk.LEFT)
        ttk.Button(questions_btn_frame, text="Edit", command=self._edit_question).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(questions_btn_frame, text="Remove", command=self._remove_question).pack(side=tk.LEFT, padx=(6, 0))

        self.project_tab.columnconfigure(1, weight=1)

    def _build_services_tab(self) -> None:
        header_frame = ttk.Frame(self.services_tab)
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text="Service Scopes", style="Heading.TLabel").pack(side=tk.LEFT)

        tree_frame = ttk.Frame(self.services_tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        columns = ("Service", "Type", "Hours", "Stages")
        self.services_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.services_tree.heading("Service", text="Service Name")
        self.services_tree.heading("Type", text="Service Type")
        self.services_tree.heading("Hours", text="Labor Hours (Low–High)")
        self.services_tree.heading("Stages", text="Stage Returns")
        self.services_tree.column("Service", width=220)
        self.services_tree.column("Type", width=200)
        self.services_tree.column("Hours", width=180)
        self.services_tree.column("Stages", width=120, anchor=tk.CENTER)
        self.services_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.services_tree.yview)
        self.services_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(self.services_tab)
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_frame, text="Add Service", command=self._add_service).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Edit", command=self._edit_service).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btn_frame, text="Remove", command=self._remove_service).pack(side=tk.LEFT, padx=(8, 0))

    def _build_attachments_tab(self) -> None:
        ttk.Label(self.attachments_tab, text="Client Attachments", style="Heading.TLabel").pack(anchor=tk.W)

        tree_frame = ttk.Frame(self.attachments_tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        columns = ("Kind", "Path", "Description")
        self.attachments_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.attachments_tree.heading("Kind", text="Type")
        self.attachments_tree.heading("Path", text="File / Reference")
        self.attachments_tree.heading("Description", text="Notes")
        self.attachments_tree.column("Kind", width=120)
        self.attachments_tree.column("Path", width=340)
        self.attachments_tree.column("Description", width=260)
        self.attachments_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.attachments_tree.yview)
        self.attachments_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(self.attachments_tab)
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_frame, text="Add", command=self._add_attachment).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Edit", command=self._edit_attachment).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btn_frame, text="Remove", command=self._remove_attachment).pack(side=tk.LEFT, padx=(8, 0))

    def _build_preview_tab(self) -> None:
        ttk.Label(self.preview_tab, text="Formatted Estimate", style="Heading.TLabel").pack(anchor=tk.W)

        self.preview_text = tk.Text(self.preview_tab, wrap=tk.WORD, state=tk.DISABLED)
        self.preview_text.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        action_frame = ttk.Frame(self.preview_tab)
        action_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(action_frame, text="Copy to Clipboard", command=self._copy_estimate).pack(side=tk.LEFT)
        ttk.Button(action_frame, text="Save Markdown", command=self._save_estimate).pack(side=tk.LEFT, padx=(8, 0))

    # -- listbox helpers -------------------------------------------------
    def _add_site_condition(self) -> None:
        value = simpledialog.askstring("Add Site Condition", "Enter site condition detail:", parent=self.root)
        if value:
            trimmed = value.strip()
            if trimmed:
                self.site_conditions.append(trimmed)
                self.site_conditions_listbox.insert(tk.END, trimmed)

    def _edit_site_condition(self) -> None:
        selection = self.site_conditions_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        current = self.site_conditions[index]
        updated = simpledialog.askstring(
            "Edit Site Condition", "Update detail:", initialvalue=current, parent=self.root
        )
        if updated:
            trimmed = updated.strip()
            if trimmed:
                self.site_conditions[index] = trimmed
                self.site_conditions_listbox.delete(index)
                self.site_conditions_listbox.insert(index, trimmed)

    def _remove_site_condition(self) -> None:
        selection = self.site_conditions_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self.site_conditions_listbox.delete(index)
        del self.site_conditions[index]

    def _add_question(self) -> None:
        value = simpledialog.askstring("Add Clarifying Question", "Enter question:", parent=self.root)
        if value:
            trimmed = value.strip()
            if trimmed:
                self.clarifying_questions.append(trimmed)
                self.questions_listbox.insert(tk.END, trimmed)

    def _edit_question(self) -> None:
        selection = self.questions_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        current = self.clarifying_questions[index]
        updated = simpledialog.askstring(
            "Edit Clarifying Question", "Update question:", initialvalue=current, parent=self.root
        )
        if updated:
            trimmed = updated.strip()
            if trimmed:
                self.clarifying_questions[index] = trimmed
                self.questions_listbox.delete(index)
                self.questions_listbox.insert(index, trimmed)

    def _remove_question(self) -> None:
        selection = self.questions_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self.questions_listbox.delete(index)
        del self.clarifying_questions[index]

    # -- attachment helpers ---------------------------------------------
    def _refresh_attachments_tree(self) -> None:
        for item in self.attachments_tree.get_children():
            self.attachments_tree.delete(item)
        for idx, attachment in enumerate(self.attachments):
            description = attachment.description or ""
            self.attachments_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(attachment.kind.title(), attachment.path, description),
            )

    def _add_attachment(self) -> None:
        dialog = AttachmentDialog(self.root)
        result = dialog.show()
        if result:
            self.attachments.append(result)
            self._refresh_attachments_tree()

    def _edit_attachment(self) -> None:
        selection = self.attachments_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        dialog = AttachmentDialog(self.root, self.attachments[index])
        result = dialog.show()
        if result:
            self.attachments[index] = result
            self._refresh_attachments_tree()

    def _remove_attachment(self) -> None:
        selection = self.attachments_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        del self.attachments[index]
        self._refresh_attachments_tree()

    # -- service helpers -------------------------------------------------
    def _refresh_services_tree(self) -> None:
        for item in self.services_tree.get_children():
            self.services_tree.delete(item)
        for idx, service in enumerate(self.services):
            hours_low = sum(phase.hours_low for phase in service.breakdown)
            hours_high = sum(phase.hours_high for phase in service.breakdown)
            if abs(hours_high - hours_low) < 1e-6:
                hours_display = f"{hours_low:.1f}"
            else:
                hours_display = f"{hours_low:.1f}–{hours_high:.1f}"
            self.services_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(service.name, service.service_type, hours_display, service.stage_returns),
            )

    def _add_service(self) -> None:
        dialog = ServiceEditor(self.root, self._available_service_types)
        result = dialog.show()
        if result:
            self.services.append(result)
            self._refresh_services_tree()

    def _edit_service(self) -> None:
        selection = self.services_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        dialog = ServiceEditor(self.root, self._available_service_types, self.services[index])
        result = dialog.show()
        if result:
            self.services[index] = result
            self._refresh_services_tree()

    def _remove_service(self) -> None:
        selection = self.services_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        del self.services[index]
        self._refresh_services_tree()

    # -- estimate generation --------------------------------------------
    def _generate_estimate(self) -> None:
        client_name = self.client_name_var.get().strip()
        if not client_name:
            messagebox.showerror("Missing Client", "Client name is required to build an estimate.")
            return
        if not self.services:
            messagebox.showerror("Missing Services", "At least one service scope must be defined.")
            return

        request_description = self.request_summary.get("1.0", tk.END).strip()

        payload: dict[str, object] = {
            "client_name": client_name,
            "project_address": self.project_address_var.get().strip() or None,
            "request_description": request_description,
            "services": [service.to_dict() for service in self.services],
        }
        if self.site_conditions:
            payload["site_conditions"] = list(self.site_conditions)
        if self.clarifying_questions:
            payload["clarifying_questions"] = list(self.clarifying_questions)
        if self.attachments:
            payload["attachments"] = [attachment.to_dict() for attachment in self.attachments]

        try:
            project = ProjectInput.from_dict(payload)
        except Exception as exc:  # pragma: no cover - interactive validation
            messagebox.showerror("Invalid Data", f"Unable to build project: {exc}")
            return

        estimator = Estimator()
        project_estimate = estimator.build_estimate(project)
        estimate_text = format_estimate(project_estimate)

        self._set_preview_text(estimate_text)
        self._last_estimate_text = estimate_text
        self._last_request_payload = payload
        messagebox.showinfo("Estimate Ready", "Estimate generated successfully. Review the preview tab.")

    def _set_preview_text(self, content: str) -> None:
        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert(tk.END, content)
        self.preview_text.configure(state=tk.DISABLED)

    def _copy_estimate(self) -> None:
        if not self._last_estimate_text:
            messagebox.showwarning("No Estimate", "Generate an estimate before copying.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self._last_estimate_text)
        messagebox.showinfo("Copied", "Estimate copied to clipboard.")

    def _save_estimate(self) -> None:
        if not self._last_estimate_text:
            messagebox.showwarning("No Estimate", "Generate an estimate before saving.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save Estimate",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")],
        )
        if filename:
            with open(filename, "w", encoding="utf-8") as fh:
                fh.write(self._last_estimate_text)
            messagebox.showinfo("Saved", f"Estimate saved to {filename}")

    def _export_request(self) -> None:
        if not self._last_request_payload:
            confirm = messagebox.askyesno(
                "No Generated Estimate",
                "An estimate has not been generated. Export current inputs to JSON?",
            )
            if not confirm:
                return
            payload: dict[str, object] = {
                "client_name": self.client_name_var.get().strip() or "Client",
                "project_address": self.project_address_var.get().strip() or None,
                "request_description": self.request_summary.get("1.0", tk.END).strip(),
                "services": [service.to_dict() for service in self.services],
            }
            if self.site_conditions:
                payload["site_conditions"] = list(self.site_conditions)
            if self.clarifying_questions:
                payload["clarifying_questions"] = list(self.clarifying_questions)
            if self.attachments:
                payload["attachments"] = [attachment.to_dict() for attachment in self.attachments]
        else:
            payload = self._last_request_payload

        filename = filedialog.asksaveasfilename(
            title="Export Request JSON", defaultextension=".json", filetypes=[("JSON", "*.json")]
        )
        if filename:
            import json

            with open(filename, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            messagebox.showinfo("Exported", f"Request data saved to {filename}")





class AttachmentDialog:
    """Dialog for creating or editing an attachment entry."""

    def __init__(self, master: tk.Misc, attachment: Optional[AttachmentData] = None) -> None:
        self.master = master
        self.attachment = attachment
        self.result: Optional[AttachmentData] = None

        self.top = tk.Toplevel(master)
        self.top.title("Attachment")
        self.top.transient(master)
        self.top.grab_set()

        frame = ttk.Frame(self.top, padding=16)
        frame.grid(row=0, column=0, sticky=tk.NSEW)
        self.top.columnconfigure(0, weight=1)
        self.top.rowconfigure(0, weight=1)

        ttk.Label(frame, text="File Path or Reference:").grid(row=0, column=0, sticky=tk.W)
        self.path_var = tk.StringVar(value=attachment.path if attachment else "")
        path_entry = ttk.Entry(frame, textvariable=self.path_var, width=50)
        path_entry.grid(row=1, column=0, sticky=tk.EW)

        browse_btn = ttk.Button(frame, text="Browse…", command=self._browse)
        browse_btn.grid(row=1, column=1, padx=(8, 0))

        ttk.Label(frame, text="Attachment Type:").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        self.kind_var = tk.StringVar(value=attachment.kind if attachment else "photo")
        kind_values = ("photo", "drawing", "measurement", "other")
        self.kind_combo = ttk.Combobox(frame, textvariable=self.kind_var, values=kind_values, width=18)
        self.kind_combo.grid(row=3, column=0, sticky=tk.W)

        ttk.Label(frame, text="Description / Notes:").grid(row=4, column=0, sticky=tk.W, pady=(8, 0))
        self.description_var = tk.StringVar(value=attachment.description if attachment else "")
        desc_entry = ttk.Entry(frame, textvariable=self.description_var, width=50)
        desc_entry.grid(row=5, column=0, columnspan=2, sticky=tk.EW)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=6, column=0, columnspan=2, sticky=tk.E, pady=(16, 0))
        ttk.Button(button_frame, text="Cancel", command=self.top.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Save", command=self._on_save).pack(side=tk.RIGHT, padx=(0, 8))

        frame.columnconfigure(0, weight=1)
        path_entry.focus_set()

    def _browse(self) -> None:
        filename = filedialog.askopenfilename(title="Select Attachment")
        if filename:
            self.path_var.set(filename)

    def _on_save(self) -> None:
        path = self.path_var.get().strip()
        if not path:
            messagebox.showerror(
                "Missing Path",
                "Provide a file path or reference for the attachment.",
                parent=self.top,
            )
            return
        kind = self.kind_var.get().strip() or "photo"
        description = self.description_var.get().strip() or None
        self.result = AttachmentData(path=path, kind=kind, description=description)
        self.top.destroy()

    def show(self) -> Optional[AttachmentData]:
        self.master.wait_window(self.top)
        return self.result


class ServiceEditor:
    """Dialog for creating or editing a service scope."""

    def __init__(
        self,
        master: tk.Misc,
        service_types: List[str],
        service: Optional[ServiceData] = None,
    ) -> None:
        self.master = master
        self.service_types = service_types
        self.initial_service = service
        self.result: Optional[ServiceData] = None

        self.top = tk.Toplevel(master)
        self.top.title("Service Scope")
        self.top.transient(master)
        self.top.grab_set()
        self.top.geometry("860x640")

        default_type = service.service_type if service else (service_types[0] if service_types else "")
        self.name_var = tk.StringVar(value=service.name if service else "")
        self.service_type_var = tk.StringVar(value=default_type)
        self.stage_returns_var = tk.IntVar(value=service.stage_returns if service else 0)
        self.permit_required_var = tk.BooleanVar(value=service.permit_required if service else False)
        self.market_low_var = tk.StringVar(
            value=str(service.market_rate_low) if service and service.market_rate_low is not None else ""
        )
        self.market_high_var = tk.StringVar(
            value=str(service.market_rate_high) if service and service.market_rate_high is not None else ""
        )
        self.notes_seed = service.notes if service and service.notes else ""

        self.breakdown: List[LaborPhaseData] = (
            [LaborPhaseData(**vars(item)) for item in service.breakdown] if service else []
        )
        self.materials: List[MaterialData] = (
            [MaterialData(**vars(item)) for item in service.materials] if service else []
        )
        self.assumptions: List[str] = list(service.assumptions) if service else []
        self.exclusions: List[str] = list(service.exclusions) if service else []

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.top, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.X)

        ttk.Label(info_frame, text="Service Name:").grid(row=0, column=0, sticky=tk.W)
        name_entry = ttk.Entry(info_frame, textvariable=self.name_var, width=28)
        name_entry.grid(row=1, column=0, sticky=tk.W)

        ttk.Label(info_frame, text="Service Type:").grid(row=0, column=1, sticky=tk.W, padx=(12, 0))
        type_combo = ttk.Combobox(
            info_frame,
            textvariable=self.service_type_var,
            values=self.service_types,
            width=26,
        )
        type_combo.grid(row=1, column=1, sticky=tk.W, padx=(12, 0))
        type_combo.configure(state="normal")

        ttk.Label(info_frame, text="Stage Returns:").grid(row=0, column=2, sticky=tk.W, padx=(12, 0))
        ttk.Spinbox(info_frame, textvariable=self.stage_returns_var, from_=0, to=10, width=5).grid(
            row=1, column=2, sticky=tk.W, padx=(12, 0)
        )

        ttk.Checkbutton(info_frame, text="Permit Required", variable=self.permit_required_var).grid(
            row=1, column=3, sticky=tk.W, padx=(12, 0)
        )

        ttk.Label(info_frame, text="Market Rate Override (Low / High)").grid(
            row=2, column=0, columnspan=2, sticky=tk.W, pady=(12, 0)
        )
        rate_frame = ttk.Frame(info_frame)
        rate_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W)
        ttk.Entry(rate_frame, textvariable=self.market_low_var, width=12).pack(side=tk.LEFT)
        ttk.Label(rate_frame, text=" to ").pack(side=tk.LEFT)
        ttk.Entry(rate_frame, textvariable=self.market_high_var, width=12).pack(side=tk.LEFT)

        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.breakdown_tab = ttk.Frame(notebook)
        notebook.add(self.breakdown_tab, text="Labor Breakdown")
        self.materials_tab = ttk.Frame(notebook)
        notebook.add(self.materials_tab, text="Materials")
        self.notes_tab = ttk.Frame(notebook)
        notebook.add(self.notes_tab, text="Assumptions & Exclusions")

        self._build_breakdown_tab()
        self._build_materials_tab()
        self._build_notes_tab()

        ttk.Label(frame, text="Internal Notes (optional):").pack(anchor=tk.W, pady=(12, 0))
        self.notes_text = tk.Text(frame, height=3)
        self.notes_text.pack(fill=tk.X)
        if self.notes_seed:
            self.notes_text.insert(tk.END, self.notes_seed)

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(button_frame, text="Cancel", command=self.top.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Save Service", command=self._on_save).pack(side=tk.RIGHT, padx=(0, 8))

        name_entry.focus_set()

    def _build_breakdown_tab(self) -> None:
        frame = self.breakdown_tab
        frame.columnconfigure(0, weight=1)

        columns = ("Phase", "Description", "Low", "High")
        self.breakdown_tree = ttk.Treeview(
            frame, columns=columns, show="headings", selectmode="browse"
        )
        for col, heading in zip(columns, ("Phase", "Description", "Low Hours", "High Hours")):
            self.breakdown_tree.heading(col, text=heading)
        self.breakdown_tree.column("Phase", width=140)
        self.breakdown_tree.column("Description", width=320)
        self.breakdown_tree.column("Low", width=100, anchor=tk.CENTER)
        self.breakdown_tree.column("High", width=100, anchor=tk.CENTER)
        self.breakdown_tree.grid(row=0, column=0, sticky=tk.NSEW)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.breakdown_tree.yview)
        self.breakdown_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Button(btn_frame, text="Add Phase", command=self._add_phase).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Edit", command=self._edit_phase).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btn_frame, text="Remove", command=self._remove_phase).pack(side=tk.LEFT, padx=(8, 0))

        self._refresh_breakdown_tree()

    def _build_materials_tab(self) -> None:
        frame = self.materials_tab
        frame.columnconfigure(0, weight=1)

        columns = ("Name", "Qty", "Unit", "Low", "High", "Notes")
        self.materials_tree = ttk.Treeview(
            frame, columns=columns, show="headings", selectmode="browse"
        )
        headings = (
            "Material",
            "Quantity",
            "Unit",
            "Unit Cost (Low)",
            "Unit Cost (High)",
            "Notes",
        )
        for col, heading in zip(columns, headings):
            self.materials_tree.heading(col, text=heading)
        self.materials_tree.column("Name", width=200)
        self.materials_tree.column("Qty", width=80, anchor=tk.CENTER)
        self.materials_tree.column("Unit", width=80, anchor=tk.CENTER)
        self.materials_tree.column("Low", width=140, anchor=tk.CENTER)
        self.materials_tree.column("High", width=140, anchor=tk.CENTER)
        self.materials_tree.column("Notes", width=240)
        self.materials_tree.grid(row=0, column=0, sticky=tk.NSEW)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.materials_tree.yview)
        self.materials_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Button(btn_frame, text="Add Material", command=self._add_material).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Edit", command=self._edit_material).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btn_frame, text="Remove", command=self._remove_material).pack(side=tk.LEFT, padx=(8, 0))

        self._refresh_materials_tree()

    def _build_notes_tab(self) -> None:
        frame = self.notes_tab
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)

        ttk.Label(frame, text="Assumptions").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame, text="Exclusions").grid(row=0, column=2, sticky=tk.W)

        self.assumptions_listbox = tk.Listbox(frame, height=10)
        self.assumptions_listbox.grid(row=1, column=0, sticky=tk.NSEW)
        self.exclusions_listbox = tk.Listbox(frame, height=10)
        self.exclusions_listbox.grid(row=1, column=2, sticky=tk.NSEW)

        for item in self.assumptions:
            self.assumptions_listbox.insert(tk.END, item)
        for item in self.exclusions:
            self.exclusions_listbox.insert(tk.END, item)

        assump_btns = ttk.Frame(frame)
        assump_btns.grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Button(
            assump_btns,
            text="Add",
            command=lambda: self._add_text_item(self.assumptions, self.assumptions_listbox, "Assumption"),
        ).pack(side=tk.LEFT)
        ttk.Button(
            assump_btns,
            text="Edit",
            command=lambda: self._edit_text_item(self.assumptions, self.assumptions_listbox, "Assumption"),
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(
            assump_btns,
            text="Remove",
            command=lambda: self._remove_text_item(self.assumptions, self.assumptions_listbox),
        ).pack(side=tk.LEFT, padx=(8, 0))

        excl_btns = ttk.Frame(frame)
        excl_btns.grid(row=2, column=2, sticky=tk.W, pady=(8, 0))
        ttk.Button(
            excl_btns,
            text="Add",
            command=lambda: self._add_text_item(self.exclusions, self.exclusions_listbox, "Exclusion"),
        ).pack(side=tk.LEFT)
        ttk.Button(
            excl_btns,
            text="Edit",
            command=lambda: self._edit_text_item(self.exclusions, self.exclusions_listbox, "Exclusion"),
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(
            excl_btns,
            text="Remove",
            command=lambda: self._remove_text_item(self.exclusions, self.exclusions_listbox),
        ).pack(side=tk.LEFT, padx=(8, 0))

    def _refresh_breakdown_tree(self) -> None:
        for item in self.breakdown_tree.get_children():
            self.breakdown_tree.delete(item)
        for idx, phase in enumerate(self.breakdown):
            self.breakdown_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(
                    phase.phase,
                    phase.description,
                    f"{phase.hours_low:.1f}",
                    f"{phase.hours_high:.1f}",
                ),
            )

    def _refresh_materials_tree(self) -> None:
        for item in self.materials_tree.get_children():
            self.materials_tree.delete(item)
        for idx, material in enumerate(self.materials):
            self.materials_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(
                    material.name,
                    f"{material.quantity:g}",
                    material.unit or "",
                    f"${material.unit_cost_low:,.2f}",
                    f"${material.unit_cost_high:,.2f}" if material.unit_cost_high is not None else "",
                    material.notes or "",
                ),
            )

    def _add_phase(self) -> None:
        dialog = PhaseDialog(self.top)
        result = dialog.show()
        if result:
            self.breakdown.append(result)
            self._refresh_breakdown_tree()

    def _edit_phase(self) -> None:
        selection = self.breakdown_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        dialog = PhaseDialog(self.top, self.breakdown[index])
        result = dialog.show()
        if result:
            self.breakdown[index] = result
            self._refresh_breakdown_tree()

    def _remove_phase(self) -> None:
        selection = self.breakdown_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        del self.breakdown[index]
        self._refresh_breakdown_tree()

    def _add_material(self) -> None:
        dialog = MaterialDialog(self.top)
        result = dialog.show()
        if result:
            self.materials.append(result)
            self._refresh_materials_tree()

    def _edit_material(self) -> None:
        selection = self.materials_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        dialog = MaterialDialog(self.top, self.materials[index])
        result = dialog.show()
        if result:
            self.materials[index] = result
            self._refresh_materials_tree()

    def _remove_material(self) -> None:
        selection = self.materials_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        del self.materials[index]
        self._refresh_materials_tree()

    def _add_text_item(self, store: List[str], listbox: tk.Listbox, label: str) -> None:
        value = simpledialog.askstring(f"Add {label}", f"Enter {label.lower()}:", parent=self.top)
        if value:
            trimmed = value.strip()
            if trimmed:
                store.append(trimmed)
                listbox.insert(tk.END, trimmed)

    def _edit_text_item(self, store: List[str], listbox: tk.Listbox, label: str) -> None:
        selection = listbox.curselection()
        if not selection:
            return
        index = selection[0]
        current = store[index]
        updated = simpledialog.askstring(
            f"Edit {label}", f"Update {label.lower()}:", initialvalue=current, parent=self.top
        )
        if updated:
            trimmed = updated.strip()
            if trimmed:
                store[index] = trimmed
                listbox.delete(index)
                listbox.insert(index, trimmed)

    def _remove_text_item(self, store: List[str], listbox: tk.Listbox) -> None:
        selection = listbox.curselection()
        if not selection:
            return
        index = selection[0]
        del store[index]
        listbox.delete(index)

    def _on_save(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Missing Name", "Service name is required.", parent=self.top)
            return
        service_type = self.service_type_var.get().strip() or "general_carpentry"
        if not self.breakdown:
            messagebox.showerror(
                "Missing Labor Breakdown",
                "Add at least one labor phase to estimate this service.",
                parent=self.top,
            )
            return

        try:
            market_low = float(self.market_low_var.get().strip()) if self.market_low_var.get().strip() else None
        except ValueError:
            messagebox.showerror("Invalid Value", "Market rate low must be numeric.", parent=self.top)
            return
        try:
            market_high = float(self.market_high_var.get().strip()) if self.market_high_var.get().strip() else None
        except ValueError:
            messagebox.showerror("Invalid Value", "Market rate high must be numeric.", parent=self.top)
            return

        notes_value = self.notes_text.get("1.0", tk.END).strip() or None

        self.result = ServiceData(
            name=name,
            service_type=service_type,
            breakdown=[LaborPhaseData(**vars(item)) for item in self.breakdown],
            materials=[MaterialData(**vars(item)) for item in self.materials],
            assumptions=list(self.assumptions),
            exclusions=list(self.exclusions),
            stage_returns=max(0, int(self.stage_returns_var.get())),
            permit_required=bool(self.permit_required_var.get()),
            notes=notes_value,
            market_rate_low=market_low,
            market_rate_high=market_high,
        )
        self.top.destroy()

    def show(self) -> Optional[ServiceData]:
        self.master.wait_window(self.top)
        return self.result


class PhaseDialog:
    """Dialog for editing a single labor phase."""

    def __init__(self, master: tk.Misc, phase: Optional[LaborPhaseData] = None) -> None:
        self.master = master
        self.phase = phase
        self.result: Optional[LaborPhaseData] = None

        self.top = tk.Toplevel(master)
        self.top.title("Labor Phase")
        self.top.transient(master)
        self.top.grab_set()

        frame = ttk.Frame(self.top, padding=16)
        frame.grid(row=0, column=0, sticky=tk.NSEW)
        self.top.columnconfigure(0, weight=1)
        self.top.rowconfigure(0, weight=1)

        ttk.Label(frame, text="Phase Name:").grid(row=0, column=0, sticky=tk.W)
        self.phase_var = tk.StringVar(value=phase.phase if phase else "")
        ttk.Entry(frame, textvariable=self.phase_var, width=24).grid(row=1, column=0, sticky=tk.W)

        ttk.Label(frame, text="Description:").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        self.description_var = tk.StringVar(value=phase.description if phase else "")
        ttk.Entry(frame, textvariable=self.description_var, width=50).grid(row=3, column=0, sticky=tk.EW)

        hours_frame = ttk.Frame(frame)
        hours_frame.grid(row=4, column=0, sticky=tk.W, pady=(12, 0))
        ttk.Label(hours_frame, text="Low Hours:").grid(row=0, column=0, sticky=tk.W)
        self.low_var = tk.StringVar(
            value=str(phase.hours_low) if phase else ""
        )
        ttk.Entry(hours_frame, textvariable=self.low_var, width=8).grid(row=1, column=0, sticky=tk.W)

        ttk.Label(hours_frame, text="High Hours:").grid(row=0, column=1, sticky=tk.W, padx=(12, 0))
        self.high_var = tk.StringVar(
            value=str(phase.hours_high) if phase else ""
        )
        ttk.Entry(hours_frame, textvariable=self.high_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=(12, 0))

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, sticky=tk.E, pady=(16, 0))
        ttk.Button(button_frame, text="Cancel", command=self.top.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Save", command=self._on_save).pack(side=tk.RIGHT, padx=(0, 8))

        frame.columnconfigure(0, weight=1)

    def _on_save(self) -> None:
        name = self.phase_var.get().strip() or "Phase"
        description = self.description_var.get().strip()
        low_raw = self.low_var.get().strip()
        high_raw = self.high_var.get().strip()
        try:
            low_value = float(low_raw) if low_raw else 0.0
        except ValueError:
            messagebox.showerror("Invalid Hours", "Low hours must be numeric.", parent=self.top)
            return
        try:
            high_value = float(high_raw) if high_raw else low_value
        except ValueError:
            messagebox.showerror("Invalid Hours", "High hours must be numeric.", parent=self.top)
            return
        if high_value < low_value:
            high_value = low_value
        self.result = LaborPhaseData(name, description, low_value, high_value)
        self.top.destroy()

    def show(self) -> Optional[LaborPhaseData]:
        self.master.wait_window(self.top)
        return self.result


class MaterialDialog:
    """Dialog for editing a single material line item."""

    def __init__(self, master: tk.Misc, material: Optional[MaterialData] = None) -> None:
        self.master = master
        self.material = material
        self.result: Optional[MaterialData] = None

        self.top = tk.Toplevel(master)
        self.top.title("Material Item")
        self.top.transient(master)
        self.top.grab_set()

        frame = ttk.Frame(self.top, padding=16)
        frame.grid(row=0, column=0, sticky=tk.NSEW)
        self.top.columnconfigure(0, weight=1)
        self.top.rowconfigure(0, weight=1)

        ttk.Label(frame, text="Material Name:").grid(row=0, column=0, sticky=tk.W)
        self.name_var = tk.StringVar(value=material.name if material else "")
        ttk.Entry(frame, textvariable=self.name_var, width=36).grid(row=1, column=0, sticky=tk.W)

        qty_frame = ttk.Frame(frame)
        qty_frame.grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Label(qty_frame, text="Quantity:").grid(row=0, column=0, sticky=tk.W)
        self.qty_var = tk.StringVar(value=str(material.quantity) if material else "")
        ttk.Entry(qty_frame, textvariable=self.qty_var, width=10).grid(row=1, column=0, sticky=tk.W)

        ttk.Label(qty_frame, text="Unit:").grid(row=0, column=1, sticky=tk.W, padx=(12, 0))
        self.unit_var = tk.StringVar(value=material.unit if material and material.unit else "")
        ttk.Entry(qty_frame, textvariable=self.unit_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(12, 0))

        cost_frame = ttk.Frame(frame)
        cost_frame.grid(row=3, column=0, sticky=tk.W, pady=(12, 0))
        ttk.Label(cost_frame, text="Unit Cost Low:").grid(row=0, column=0, sticky=tk.W)
        self.cost_low_var = tk.StringVar(
            value=str(material.unit_cost_low) if material else ""
        )
        ttk.Entry(cost_frame, textvariable=self.cost_low_var, width=12).grid(row=1, column=0, sticky=tk.W)

        ttk.Label(cost_frame, text="Unit Cost High:").grid(row=0, column=1, sticky=tk.W, padx=(12, 0))
        self.cost_high_var = tk.StringVar(
            value=str(material.unit_cost_high) if material and material.unit_cost_high is not None else ""
        )
        ttk.Entry(cost_frame, textvariable=self.cost_high_var, width=12).grid(row=1, column=1, sticky=tk.W, padx=(12, 0))

        factor_frame = ttk.Frame(frame)
        factor_frame.grid(row=4, column=0, sticky=tk.W, pady=(12, 0))
        ttk.Label(factor_frame, text="Waste % (optional):").grid(row=0, column=0, sticky=tk.W)
        self.waste_var = tk.StringVar(
            value=str(material.waste_factor) if material and material.waste_factor is not None else ""
        )
        ttk.Entry(factor_frame, textvariable=self.waste_var, width=10).grid(row=1, column=0, sticky=tk.W)

        ttk.Label(factor_frame, text="Price Drift % (optional):").grid(row=0, column=1, sticky=tk.W, padx=(12, 0))
        self.drift_var = tk.StringVar(
            value=str(material.price_drift) if material and material.price_drift is not None else ""
        )
        ttk.Entry(factor_frame, textvariable=self.drift_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(12, 0))

        ttk.Label(frame, text="Notes:").grid(row=5, column=0, sticky=tk.W, pady=(12, 0))
        self.notes_var = tk.StringVar(value=material.notes if material and material.notes else "")
        ttk.Entry(frame, textvariable=self.notes_var, width=50).grid(row=6, column=0, sticky=tk.EW)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=7, column=0, sticky=tk.E, pady=(16, 0))
        ttk.Button(button_frame, text="Cancel", command=self.top.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Save", command=self._on_save).pack(side=tk.RIGHT, padx=(0, 8))

        frame.columnconfigure(0, weight=1)

    def _on_save(self) -> None:
        name = self.name_var.get().strip() or "Material"
        try:
            quantity = float(self.qty_var.get().strip() or 0.0)
        except ValueError:
            messagebox.showerror("Invalid Quantity", "Quantity must be numeric.", parent=self.top)
            return
        try:
            unit_cost_low = float(self.cost_low_var.get().strip()) if self.cost_low_var.get().strip() else 0.0
        except ValueError:
            messagebox.showerror("Invalid Cost", "Unit cost low must be numeric.", parent=self.top)
            return
        try:
            unit_cost_high = (
                float(self.cost_high_var.get().strip()) if self.cost_high_var.get().strip() else None
            )
        except ValueError:
            messagebox.showerror("Invalid Cost", "Unit cost high must be numeric.", parent=self.top)
            return
        try:
            waste = float(self.waste_var.get().strip()) if self.waste_var.get().strip() else None
        except ValueError:
            messagebox.showerror("Invalid Waste", "Waste must be numeric.", parent=self.top)
            return
        try:
            drift = float(self.drift_var.get().strip()) if self.drift_var.get().strip() else None
        except ValueError:
            messagebox.showerror("Invalid Drift", "Price drift must be numeric.", parent=self.top)
            return

        unit = self.unit_var.get().strip() or None
        notes = self.notes_var.get().strip() or None

        self.result = MaterialData(
            name=name,
            quantity=quantity,
            unit_cost_low=unit_cost_low,
            unit_cost_high=unit_cost_high,
            unit=unit,
            waste_factor=waste,
            price_drift=drift,
            notes=notes,
        )
        self.top.destroy()

    def show(self) -> Optional[MaterialData]:
        self.master.wait_window(self.top)
        return self.result
