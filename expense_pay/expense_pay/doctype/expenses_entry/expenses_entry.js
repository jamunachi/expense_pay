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
    account_currency_from: function (frm) {
        if (frm.doc.account_currency_from) {
            // Fetch the latest exchange rate
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Currency Exchange",
                    filters: {
                        from_currency: frm.doc.account_currency_from,
                    },
                    fields: ["name", "exchange_rate", "date"],
                    order_by: "date desc",
                    limit_page_length: 1,
                },
                callback: function (r) {
                    if (r.message && r.message.length > 0) {
                        var latest_exchange = r.message[0];
                        // Update fields in your doctype
                        frappe.model.set_value(
                            frm.doctype,
                            frm.docname,
                            "exchange_rate",
                            latest_exchange.exchange_rate
                        );
                        frappe.model.set_value(
                            frm.doctype,
                            frm.docname,
                            "exchange_rate_date",
                            latest_exchange.date
                        );
                        frappe.model.set_value(
                            frm.doctype,
                            frm.docname,
                            "currency_exchange_link",
                            latest_exchange.name
                        );
                    }
                },
            });
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

        frappe.model.set_value(
            cdt,
            cdn,
            "exchange_rate_date",
            frm.doc.exchange_rate_date
        );

        frappe.model.set_value(
            cdt,
            cdn,
            "currency_exchange_link",
            frm.doc.currency_exchange_link
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
        if (row.exchange_rate_date.length === 0 && frm.doc.multi_currency) {
            frappe.model.set_value(
                cdt,
                cdn,
                "exchange_rate_date",
                frm.doc.exchange_rate_date
            );
        }
        if (row.currency_exchange_link.length === 0 && frm.doc.multi_currency) {
            frappe.model.set_value(
                cdt,
                cdn,
                "currency_exchange_link",
                frm.doc.currency_exchange_link
            );
        }

        frm.fields_dict.expenses.grid.update_docfield_property(
            "amount",
            "reqd",
            1
        );
    },
    account_currency: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (frm.doc.multi_currency) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Currency Exchange",
                    filters: {
                        from_currency: row.account_currency,
                    },
                    fields: ["name", "exchange_rate", "date"],
                    order_by: "date desc",
                    limit_page_length: 1,
                },
                callback: function (r) {
                    if (r.message && r.message.length > 0) {
                        var latest_exchange = r.message[0];
                        // Update fields in your doctype
                        frappe.model.set_value(
                            cdt,
                            cdn,
                            "exchange_rate",
                            latest_exchange.exchange_rate
                        );
                        frappe.model.set_value(
                            cdt,
                            cdn,
                            "exchange_rate_date",
                            latest_exchange.date
                        );
                        frappe.model.set_value(
                            cdt,
                            cdn,
                            "currency_exchange_link",
                            latest_exchange.name
                        );
                    }
                },
            });
        }
    },
});
