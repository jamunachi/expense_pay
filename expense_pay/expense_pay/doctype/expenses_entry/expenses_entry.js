// Copyright (c) 2023, Kishan Panchal and contributors
// For license information, please see license.txt

frappe.ui.form.on("Expenses Entry", {
    refresh: function (frm) {
        frm.events.show_general_ledger(frm);
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
    multi_currency: function (frm) {
        if (frm.doc.multi_currency) {
            frm.toggle_reqd("exchange_rate", frm.doc.multi_currency);
            frm.toggle_reqd(
                "paid_amount_in_account_currency",
                frm.doc.multi_currency
            );
            var fields = [
                "account_paid_to",
                "amount",
                "amount_in_account_currency",
                "exchange_rate",
                "remarks",
                "cost_center",
                "project",
            ];
            var grid = frm.get_field("expenses").grid;
            if (grid) grid.set_column_disp(fields, frm.doc.multi_currency);

            var df = frappe.meta.get_docfield(
                "Expenses",
                "amount",
                cur_frm.doc.name
            );
            df.read_only = 1;

            frm.fields_dict.expenses.grid.update_docfield_property(
                "account_currency",
                "reqd",
                1
            );

            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount",
                "reqd",
                1
            );

            frm.fields_dict.expenses.grid.update_docfield_property(
                "exchange_rate",
                "reqd",
                1
            );

            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount_in_account_currency",
                "reqd",
                1
            );
        } else {
            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount",
                "read_only",
                0
            );
            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount",
                "reqd",
                1
            );

            frm.toggle_reqd("exchange_rate", frm.doc.multi_currency);
            frm.toggle_reqd(
                "paid_amount_in_account_currency",
                frm.doc.multi_currency
            );
        }
    },
    paid_amount_in_account_currency: function (frm) {
        if (frm.doc.paid_amount_in_account_currency) {
            //    set paid_amount valur to the paid_amount_in_account_currency field * exchange_rate
            frm.set_value(
                "paid_amount",
                frm.doc.paid_amount_in_account_currency * frm.doc.exchange_rate
            );
            // frm.refresh_field("expenses");
        }
    },
});

frappe.ui.form.on("Expenses", {
    onload: function (frm) {
        frm.fields_dict["expenses"].grid.get_field(
            "account_paid_to"
        ).get_query = function (doc, cdt, cdn) {
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
    amount_in_account_currency: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        frappe.model.set_value(
            cdt,
            cdn,
            "amount",
            d.amount_in_account_currency * d.exchange_rate
        );
    },
    expenses_add: function (frm, cdt, cdn) {
        // set the account_currency value to the account_currency field and exchange_rate to the exchange_rate field
        console.log("expenses_add");
        frappe.model.set_value(
            cdt,
            cdn,
            "account_currency",
            frm.doc.account_currency_from
        );
        frappe.model.set_value(
            cdt,
            cdn,
            "exchange_rate",
            frm.doc.exchange_rate
        );
    },
    form_render: function (frm, cdt, cdn) {
        // set the exchange_rate value to the exchange_rate field
        var row = locals[cdt][cdn];
        console.log("exchange_rate_on_form_rendered");
        if (row.account_currency.length === 0 && frm.doc.multi_currency) {
            frappe.model.set_value(
                cdt,
                cdn,
                "exchange_rate",
                frm.doc.exchange_rate
            );
        }
        if (row.exchange_rate.length === 0 && frm.doc.multi_currency) {
            frappe.model.set_value(
                cdt,
                cdn,
                "exchange_rate",
                frm.doc.exchange_rate
            );
        }
        frm.fields_dict.expenses.grid.update_docfield_property(
            "amount",
            "reqd",
            1
        );
    },
});

function set_exchange_rate(frm, cdt, cdn) {
    var company_currency = frappe.get_doc(
        ":Company",
        frm.doc.company
    ).default_currency;
    var row = locals[cdt][cdn];

    if (row.account_currency == company_currency || !frm.doc.multi_currency) {
        row.exchange_rate = 1;
        erpnext.journal_entry.set_debit_credit_in_company_currency(
            frm,
            cdt,
            cdn
        );
    } else if (
        !row.exchange_rate ||
        row.exchange_rate == 1 ||
        row.account_type == "Bank"
    ) {
        frappe.call({
            method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_exchange_rate",
            args: {
                posting_date: frm.doc.posting_date,
                account: row.account,
                account_currency: row.account_currency,
                company: frm.doc.company,
                reference_type: cstr(row.reference_type),
                reference_name: cstr(row.reference_name),
                debit: flt(row.debit_in_account_currency),
                credit: flt(row.credit_in_account_currency),
                exchange_rate: row.exchange_rate,
            },
            callback: function (r) {
                if (r.message) {
                    row.exchange_rate = r.message;
                    erpnext.journal_entry.set_debit_credit_in_company_currency(
                        frm,
                        cdt,
                        cdn
                    );
                }
            },
        });
    } else {
        erpnext.journal_entry.set_debit_credit_in_company_currency(
            frm,
            cdt,
            cdn
        );
    }
    refresh_field("exchange_rate", cdn, "accounts");
}

function set_debit_credit_in_company_currency(frm, cdt, cdn) {
    var row = locals[cdt][cdn];

    frappe.model.set_value(
        cdt,
        cdn,
        "debit",
        flt(
            flt(row.debit_in_account_currency) * row.exchange_rate,
            precision("debit", row)
        )
    );

    frappe.model.set_value(
        cdt,
        cdn,
        "credit",
        flt(
            flt(row.credit_in_account_currency) * row.exchange_rate,
            precision("credit", row)
        )
    );

    cur_frm.cscript.update_totals(frm.doc);
}
