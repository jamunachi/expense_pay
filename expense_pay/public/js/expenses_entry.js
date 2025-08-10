// Copyright (c) 2023, Kishan Panchal and contributors
// For license information, please see license.txt

<<<<<<< HEAD
frappe.ui.form.on("Expenses Entry", {
  refresh: function (frm) {
    frm.events.show_general_ledger(frm);
=======
// Runtime filters from settings
function apply_expense_entry_filters(frm, filters) {
  const merge = (obj) => ({filters: obj});
  const company = frm.doc.company;

  // account filters
  const baseAcc = { company: company };
  if (filters.only_leaf_accounts) baseAcc["is_group"] = 0;

  // header credit account
  frm.set_query("account_paid_from", function() {
    let f = Object.assign({}, baseAcc);
    if (filters.credit_account_types && filters.credit_account_types.length) {
      f["account_type"] = ["in", filters.credit_account_types];
    }
    return merge(f);
  });

  // default cost center
  const baseCC = {};
  if (filters.only_leaf_cost_centers) baseCC["is_group"] = 0;
  frm.set_query("default_cost_center", function() {
    return merge(baseCC);
  });

  // child table
  if (frm.fields_dict && frm.fields_dict.expenses && frm.fields_dict.expenses.grid) {
    frm.fields_dict.expenses.grid.get_field("account_paid_to").get_query = function(doc, cdt, cdn) {
      let f = Object.assign({}, baseAcc);
      if (filters.debit_account_types && filters.debit_account_types.length) {
        f["account_type"] = ["in", filters.debit_account_types];
      }
      return merge(f);
    };
    frm.fields_dict.expenses.grid.get_field("cost_center").get_query = function(doc, cdt, cdn) {
      return merge(baseCC);
    };
  }
}


frappe.ui.form.on("Expenses Entry", {
  show_import_dialog: function(frm) {
    const d = new frappe.ui.Dialog({
      title: __("Import Expenses (CSV)"),
      size: "extra-large",
      fields: [
        {fieldtype:"Section Break", label: __("Download Template")},
        {fieldtype:"HTML", fieldname:"tmpl_info", options:"<div class='text-muted'>" + __("Click to download the CSV header template.") + "</div>"},
        {fieldtype:"Button", fieldname:"btn_download", label: __("Download Template")},
        {fieldtype:"Section Break", label: __("Paste CSV")},
        {fieldtype:"Code", fieldname:"csv", options:"csv", height: 240, description: __("Paste your CSV content here.")},
        {fieldtype:"Section Break", label: __("Preview")},
        {fieldtype:"HTML", fieldname:"preview_html"},
      ],
      primary_action_label: __("Import & Submit"),
      primary_action: () => {
        const csv = d.get_value("csv") || "";
        if (!csv.trim()) {
          frappe.msgprint(__("Please paste CSV content."));
          return;
        }
        d.set_primary_action(__("Working..."));
        frappe.call({
          method: "expense_pay.importer.import_expenses",
          args: { csv_content: csv, dry_run: 0 },
          callback(r) {
            d.hide();
            if (r.message && r.message.ok && !r.message.dry_run) {
              frappe.set_route("Form", "Expenses Entry", r.message.voucher);
            } else if (r.message && r.message.errors) {
              frappe.msgprint(r.message.errors.join("<br>"));
            }
          },
          always: () => d.set_primary_action(__("Import & Submit"))
        });
      }
    });

    // wire download button
    d.get_field("btn_download").$input.on("click", () => {
      frappe.call({
        method: "expense_pay.importer.download_template",
        callback(r) {
          if (!r.message) return;
          const csv = r.message;
          const blob = new Blob([csv], {type: "text/csv;charset=utf-8;"});
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "Expense_Entry_Import_Template.csv";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }
      });
    });

    // live dry run preview
    d.fields_dict.csv.editor.on("change", () => {
      const csv = d.get_value("csv") || "";
      if (!csv.trim()) { d.fields_dict.preview_html.$wrapper.html(""); return; }
      frappe.call({
        method: "expense_pay.importer.import_expenses",
        args: { csv_content: csv, dry_run: 1 },
        callback(r) {
          if (!r.message) return;
          if (r.message.ok && r.message.dry_run) {
            const rows = r.message.rows || [];
            const head = r.message.header || {};
            let html = "<div class='mb-2 text-muted'>" + __("Dry Run Preview (no data saved)") + "</div>";
            html += "<div class='mb-2'><b>" + __("Header") + ":</b> " + frappe.utils.escape_html(JSON.stringify(head)) + "</div>";
            html += "<div class='overflow-auto' style='max-height:40vh'><table class='table table-bordered table-compact'><thead><tr>" +
                    "<th>" + __("Row") + "</th><th>" + __("Account Paid To") + "</th><th>" + __("Cost Center") + "</th><th>" + __("Amount w/o VAT") + "</th><th>" + __("VAT") + "</th><th>" + __("Project") + "</th>" +
                    "</tr></thead><tbody>";
            rows.forEach((r, i) => {
               html += "<tr><td>" + (i+1) + "</td><td>" + frappe.utils.escape_html(r.account_paid_to||'') + "</td><td>" + frappe.utils.escape_html(r.cost_center||'') + "</td><td class='text-right'>" + (r.amount_without_vat||0) + "</td><td class='text-right'>" + (r.vat_amount||0) + "</td><td>" + frappe.utils.escape_html(r.project||'') + "</td></tr>";
            });
            html += "</tbody></table></div>";
            d.fields_dict.preview_html.$wrapper.html(html);
          } else if (r.message && r.message.errors) {
            d.fields_dict.preview_html.$wrapper.html("<div class='text-danger'><b>" + __("Errors") + ":</b><br>" + r.message.errors.join("<br>") + "</div>");
          }
        }
      });
    });

    d.show();
  },

  show_gl_preview: function(frm) {
    const doc = frm.doc;
    frappe.call({
      method: "expense_pay.create_gl_entry.simulate_gl_entries",
      args: { doc },
      freeze: true,
      freeze_message: __("Building preview..."),
      callback(r) {
        if (!r.message) return;
        const data = r.message;
        let rows = data.rows || [];
        let html = '<div class="mb-3 text-sm text-muted">' + __('Preview only — nothing posted yet.') + '</div>';
        html += '<div class="overflow-auto" style="max-height: 50vh">';
        html += '<table class="table table-bordered table-compact"><thead><tr>' +
                '<th>' + __('Account') + '</th>' +
                '<th class="text-right">' + __('Debit') + '</th>' +
                '<th class="text-right">' + __('Credit') + '</th>' +
                '<th>' + __('Cost Center') + '</th>' +
                '<th>' + __('Remarks') + '</th>' +
                '</tr></thead><tbody>';
        rows.forEach(rw => {
          html += '<tr><td>' + frappe.utils.escape_html(rw.account || '') + '</td>' +
                  '<td class="text-right">' + format_currency(rw.debit || 0, doc.company_currency || "") + '</td>' +
                  '<td class="text-right">' + format_currency(rw.credit || 0, doc.company_currency || "") + '</td>' +
                  '<td>' + frappe.utils.escape_html(rw.cost_center || '') + '</td>' +
                  '<td>' + frappe.utils.escape_html(rw.remarks || '') + '</td></tr>';
        });
        html += '</tbody><tfoot><tr>' +
                '<th class="text-right">' + __('Totals') + '</th>' +
                '<th class="text-right">' + format_currency(data.total_debit || 0, doc.company_currency || "") + '</th>' +
                '<th class="text-right">' + format_currency(data.total_credit || 0, doc.company_currency || "") + '</th>' +
                '<th colspan="2">' + (data.balanced ? __("Balanced") : __("Not Balanced")) + '</th>' +
                '</tr></tfoot></table></div>';
        const d = new frappe.ui.Dialog({
          title: __('GL Preview'),
          size: 'large',
          primary_action_label: __('Close'),
          primary_action() { d.hide(); }
        });
        d.$body.html(html);
        d.show();
      }
    });
  },

  refresh: function (frm) {
    frm.events.show_general_ledger(frm);
    frm.add_custom_button(__("Preview GL"), function(){ frm.events.show_gl_preview(frm); }, __("Actions"));
>>>>>>> origin/release/v1.0.0
  },
  show_general_ledger: function (frm) {
    if (frm.doc.docstatus > 0) {
      frm.add_custom_button(
        __("Ledger"),
        function () {
          frappe.route_options = {
            voucher_no: frm.doc.name,
            from_date: frm.doc.posting_date,
            to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
            company: frm.doc.company,
            group_by: "",
            show_cancelled_entries: frm.doc.docstatus === 2,
          };
          frappe.set_route("query-report", "General Ledger");
        },
        "fa fa-table"
      );
    }
  },
  onload: function (frm) {
    frm.fields_dict["account_paid_from"].get_query = function (doc) {
      return {
        filters: {
          is_group: 0,
        },
      };
    };
  },
  before_save: function (frm) {
    console.log("paid amount", frm.doc.paid_amount);
    console.log("total debit", frm.doc.total_debit);

    let rounded_paid_amount = parseFloat(frm.doc.paid_amount.toFixed(2));
    let rounded_total_debit = parseFloat(frm.doc.total_debit.toFixed(2));

    if (rounded_paid_amount !== rounded_total_debit) {
      frappe.throw(
        "Total Debit amount must be equal to or less than the Paid Amount"
      );
    }
  },
});

frappe.ui.form.on("Expenses", {
  expenses_remove: function (frm, cdt, cdn) {
    let totalAmountPromise = new Promise(function (resolve, reject) {
      let totalAmount = 0;
      frm.doc.expenses.forEach(function (d) {
        totalAmount += d.amount;
      });

      resolve(totalAmount);
    });

    totalAmountPromise.then(function (totalAmount) {
      frm.set_value("total_debit", totalAmount);
    });
  },
  onload: function (frm) {
    frm.fields_dict["expenses"].grid.get_field("account_paid_to").get_query =
      function (doc, cdt, cdn) {
        return {
          filters: {
            is_group: 0,
          },
        };
      };
  },
  amount: function (frm, cdt, cdn) {
    let d = locals[cdt][cdn];
    // sum all the amounts from the expenses table and set it to the total_debit field
    let totalAmountPromise = new Promise(function (resolve, reject) {
      let totalAmount = 0;
      frm.doc.expenses.forEach(function (d) {
        totalAmount += d.amount;
      });

      resolve(totalAmount);
    });

    totalAmountPromise.then(function (totalAmount) {
      frm.set_value("total_debit", totalAmount);
    });
  },
  account_paid_to: function (frm, cdt, cdn) {
    let d = locals[cdt][cdn];
    if (d.account_paid_to) {
      frappe.model.set_value(
        cdt,
        cdn,
        "cost_center",
        frm.doc.default_cost_center
      );
    }
  },
});
<<<<<<< HEAD
=======


frappe.ui.form.on("Expenses Entry", {
  show_import_dialog: function(frm) {
    const d = new frappe.ui.Dialog({
      title: __("Import Expenses (CSV)"),
      size: "extra-large",
      fields: [
        {fieldtype:"Section Break", label: __("Download Template")},
        {fieldtype:"HTML", fieldname:"tmpl_info", options:"<div class='text-muted'>" + __("Click to download the CSV header template.") + "</div>"},
        {fieldtype:"Button", fieldname:"btn_download", label: __("Download Template")},
        {fieldtype:"Section Break", label: __("Paste CSV")},
        {fieldtype:"Code", fieldname:"csv", options:"csv", height: 240, description: __("Paste your CSV content here.")},
        {fieldtype:"Section Break", label: __("Preview")},
        {fieldtype:"HTML", fieldname:"preview_html"},
      ],
      primary_action_label: __("Import & Submit"),
      primary_action: () => {
        const csv = d.get_value("csv") || "";
        if (!csv.trim()) {
          frappe.msgprint(__("Please paste CSV content."));
          return;
        }
        d.set_primary_action(__("Working..."));
        frappe.call({
          method: "expense_pay.importer.import_expenses",
          args: { csv_content: csv, dry_run: 0 },
          callback(r) {
            d.hide();
            if (r.message && r.message.ok && !r.message.dry_run) {
              frappe.set_route("Form", "Expenses Entry", r.message.voucher);
            } else if (r.message && r.message.errors) {
              frappe.msgprint(r.message.errors.join("<br>"));
            }
          },
          always: () => d.set_primary_action(__("Import & Submit"))
        });
      }
    });

    // wire download button
    d.get_field("btn_download").$input.on("click", () => {
      frappe.call({
        method: "expense_pay.importer.download_template",
        callback(r) {
          if (!r.message) return;
          const csv = r.message;
          const blob = new Blob([csv], {type: "text/csv;charset=utf-8;"});
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "Expense_Entry_Import_Template.csv";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }
      });
    });

    // live dry run preview
    d.fields_dict.csv.editor.on("change", () => {
      const csv = d.get_value("csv") || "";
      if (!csv.trim()) { d.fields_dict.preview_html.$wrapper.html(""); return; }
      frappe.call({
        method: "expense_pay.importer.import_expenses",
        args: { csv_content: csv, dry_run: 1 },
        callback(r) {
          if (!r.message) return;
          if (r.message.ok && r.message.dry_run) {
            const rows = r.message.rows || [];
            const head = r.message.header || {};
            let html = "<div class='mb-2 text-muted'>" + __("Dry Run Preview (no data saved)") + "</div>";
            html += "<div class='mb-2'><b>" + __("Header") + ":</b> " + frappe.utils.escape_html(JSON.stringify(head)) + "</div>";
            html += "<div class='overflow-auto' style='max-height:40vh'><table class='table table-bordered table-compact'><thead><tr>" +
                    "<th>" + __("Row") + "</th><th>" + __("Account Paid To") + "</th><th>" + __("Cost Center") + "</th><th>" + __("Amount w/o VAT") + "</th><th>" + __("VAT") + "</th><th>" + __("Project") + "</th>" +
                    "</tr></thead><tbody>";
            rows.forEach((r, i) => {
               html += "<tr><td>" + (i+1) + "</td><td>" + frappe.utils.escape_html(r.account_paid_to||'') + "</td><td>" + frappe.utils.escape_html(r.cost_center||'') + "</td><td class='text-right'>" + (r.amount_without_vat||0) + "</td><td class='text-right'>" + (r.vat_amount||0) + "</td><td>" + frappe.utils.escape_html(r.project||'') + "</td></tr>";
            });
            html += "</tbody></table></div>";
            d.fields_dict.preview_html.$wrapper.html(html);
          } else if (r.message && r.message.errors) {
            d.fields_dict.preview_html.$wrapper.html("<div class='text-danger'><b>" + __("Errors") + ":</b><br>" + r.message.errors.join("<br>") + "</div>");
          }
        }
      });
    });

    d.show();
  },

  setup: function(frm) {
    frappe.call({
      method: "expense_pay.expense_pay.doctype.expense_entry_settings.expense_entry_settings.get_ui_filters",
      callback(r) {
        if (r && r.message) {
          apply_expense_entry_filters(frm, r.message);
        }
      }
    });
  }
});
>>>>>>> origin/release/v1.0.0
