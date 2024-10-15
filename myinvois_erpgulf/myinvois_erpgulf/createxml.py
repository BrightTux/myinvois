import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
import frappe
import json


def create_invoice_with_extensions():
                
            try:
                invoice = ET.Element("Invoice", {
                    "xmlns": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
                    "xmlns:cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                    "xmlns:cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                    "xmlns:ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
                })
                return invoice
            except Exception as e:
                frappe.msgprint(f"Errorcreate invoice extensions: {str(e)}")

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
import frappe
import json


def create_element(parent, tag, text=None, attributes=None):
    element = ET.SubElement(parent, tag, attributes or {})
    if text:
        element.text = text
    return element

def get_current_utc_datetime():
    current_datetime_utc = datetime.now(timezone.utc)
    formatted_date = current_datetime_utc.strftime('%Y-%m-%d')
    formatted_time = current_datetime_utc.strftime('%H:%M:%SZ')
    return formatted_date, formatted_time

def salesinvoice_data(invoice, sales_invoice_doc):
    try:
        create_element(invoice, "cbc:ID", str(sales_invoice_doc.name))

        formatted_date, formatted_time = get_current_utc_datetime()
        create_element(invoice, "cbc:IssueDate", formatted_date)
        create_element(invoice, "cbc:IssueTime", formatted_time)

        invoice_type_code = "01" if sales_invoice_doc.is_return == 0 else "02"
        create_element(invoice, "cbc:InvoiceTypeCode", invoice_type_code, {"listVersionID": "1.0"})

        create_element(invoice, "cbc:DocumentCurrencyCode", "MYR")  # or sales_invoice_doc.currency
        create_element(invoice, "cbc:TaxCurrencyCode", "MYR")

        cac_InvoicePeriod = create_element(invoice, "cac:InvoicePeriod")
        create_element(cac_InvoicePeriod, "cbc:StartDate", str(sales_invoice_doc.posting_date))
        create_element(cac_InvoicePeriod, "cbc:EndDate", str(sales_invoice_doc.due_date))
        create_element(cac_InvoicePeriod, "cbc:Description", "Monthly")

    except Exception as e:
        frappe.msgprint(f"Error sales invoice data: {str(e)}")

# def salesinvoice_data(invoice, sales_invoice_doc):
#     try:
    
#         cbID1 = ET.SubElement(invoice, "cbc:ID")
#         cbID1.text = str(sales_invoice_doc.name) 
#         current_datetime_utc = datetime.now(timezone.utc)
#         formatted_date = current_datetime_utc.strftime('%Y-%m-%d')
#         formatted_time = current_datetime_utc.strftime('%H:%M:%SZ')

#         Date1 = ET.SubElement(invoice, "cbc:IssueDate")
#         Date1.text = formatted_date 
#         Time1 = ET.SubElement(invoice, "cbc:IssueTime")
#         Time1.text = formatted_time

#         cbc_InvoiceTypeCode1 = ET.SubElement(invoice, "cbc:InvoiceTypeCode", listVersionID="1.0")
#         if sales_invoice_doc.is_return == 0:
#                         cbc_InvoiceTypeCode1.text = "01"
#         elif sales_invoice_doc.is_return == 1:     
#                         cbc_InvoiceTypeCode1.text = "02"
        

#         Document_Currency_Code = ET.SubElement(invoice, "cbc:DocumentCurrencyCode")
#         Document_Currency_Code.text =  "MYR"                  #sales_invoice_doc.currency
#         cbc_TaxCurrencyCode1 = ET.SubElement(invoice, "cbc:TaxCurrencyCode")
#         cbc_TaxCurrencyCode1.text = "MYR"

#         cac_InvoicePeriod = ET.SubElement(invoice, "cac:InvoicePeriod")

#         start1 = ET.SubElement(cac_InvoicePeriod, "cbc:StartDate")
#         start1.text = str(sales_invoice_doc.posting_date)
#         end = ET.SubElement(cac_InvoicePeriod, "cbc:EndDate")
#         end.text = str(sales_invoice_doc.due_date)


#         cbc_Description1 = ET.SubElement(cac_InvoicePeriod, "cbc:Description")
#         cbc_Description1.text = "Monthly"

#     except Exception as e:
#         frappe.msgprint(f"Error sales invoice data: {str(e)}")

# Create billing reference
# def create_billing_reference(invoice):
#             try:


#                 cac_BillingReference = ET.SubElement(invoice, "cac:BillingReference")
#                 cac_AdditionalDocumentReference = ET.SubElement(cac_BillingReference, "cac:AdditionalDocumentReference")
#                 cbc_ID = ET.SubElement(cac_AdditionalDocumentReference, "cbc:ID")
#                 cbc_ID.text = "IV0000010178689"

#             except Exception as e:
#                 frappe.msgprint(f"Error create billing: {str(e)}")




def add_address_lines(cac_PostalAddress, address):
    if address.address_line1:
        create_element(create_element(cac_PostalAddress, "cac:AddressLine"), "cbc:Line", address.address_line1)
    if address.address_line2:
        create_element(create_element(cac_PostalAddress, "cac:AddressLine"), "cbc:Line", address.address_line2)

def company_data(invoice, sales_invoice_doc):
    try:
        settings = frappe.get_doc('LHDN Malaysia Setting')
        cac_AccountingSupplierParty = create_element(invoice, "cac:AccountingSupplierParty")
        cac_Party = create_element(cac_AccountingSupplierParty, "cac:Party")

        create_element(cac_Party, "cbc:IndustryClassificationCode", "62099", {"name": "Other information technology service activities n.e.c."})
        
        create_element(create_element(cac_Party, "cac:PartyIdentification"), "cbc:ID", str(settings.company_tin_number), {"schemeID": "TIN"})
        create_element(create_element(cac_Party, "cac:PartyIdentification"), "cbc:ID", str(settings.company_id_value), {"schemeID": str(settings.company_id_type)})

        address_list = frappe.get_list(
            "Address", 
            filters={"is_your_company_address": "1"}, 
            fields=["address_line1", "address_line2", "city", "pincode", "state", "phone", "email_id"]
        )

        if not address_list:
            frappe.throw("Invoice requires a proper address. Please add your company address in the Address field.")

        for address in address_list:
            cac_PostalAddress = create_element(cac_Party, "cac:PostalAddress")
            create_element(cac_PostalAddress, "cbc:CityName", address.city)
            create_element(cac_PostalAddress, "cbc:PostalZone", address.pincode)
            create_element(cac_PostalAddress, "cbc:CountrySubentityCode", address.state)

            add_address_lines(cac_PostalAddress, address)

            combined_city_pincode = f"{address.city}, {address.pincode}"
            create_element(create_element(cac_PostalAddress, "cac:AddressLine"), "cbc:Line", combined_city_pincode)

            cac_Country = create_element(cac_PostalAddress, "cac:Country")
            create_element(cac_Country, "cbc:IdentificationCode", "MYS", {"listAgencyID": "6", "listID": "ISO3166-1"})

        cac_PartyLegalEntity = create_element(cac_Party, "cac:PartyLegalEntity")
        create_element(cac_PartyLegalEntity, "cbc:RegistrationName", sales_invoice_doc.company)


        cac_Contact = create_element(cac_Party, "cac:Contact")
        if address.get("phone"):
            create_element(cac_Contact, "cbc:Telephone", address.phone)
        if address.get("email_id"):
            create_element(cac_Contact, "cbc:ElectronicMail", address.email_id)

    except Exception as e:
        frappe.throw(f"Error in company data generation: {str(e)}")


def add_address_to_party(cac_Party, address):
    cac_PostalAddress = create_element(cac_Party, "cac:PostalAddress")
    create_element(cac_PostalAddress, "cbc:CityName", address.city)
    create_element(cac_PostalAddress, "cbc:PostalZone", address.pincode)
    create_element(cac_PostalAddress, "cbc:CountrySubentityCode", address.state)
    if address.address_line1:
        create_element(create_element(cac_PostalAddress, "cac:AddressLine"), "cbc:Line", address.address_line1)
    if address.address_line2:
        create_element(create_element(cac_PostalAddress, "cac:AddressLine"), "cbc:Line", address.address_line2)

    combined_city_pincode = f"{address.city}, {address.pincode}"
    create_element(create_element(cac_PostalAddress, "cac:AddressLine"), "cbc:Line", combined_city_pincode)

    cac_Country = create_element(cac_PostalAddress, "cac:Country")
    create_element(cac_Country, "cbc:IdentificationCode", "MYS", {"listAgencyID": "6", "listID": "ISO3166-1"})


def customer_data(invoice, sales_invoice_doc):
    try:
        settings = frappe.get_doc('LHDN Malaysia Setting')
        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.customer)
        cac_AccountingCustomerParty = create_element(invoice, "cac:AccountingCustomerParty")
        cac_Party = create_element(cac_AccountingCustomerParty, "cac:Party")

        create_element(create_element(cac_Party, "cac:PartyIdentification"), "cbc:ID", settings.customer_tin_number, {"schemeID": "TIN"})
        create_element(create_element(cac_Party, "cac:PartyIdentification"), "cbc:ID", settings.customer_id_value, {"schemeID": settings.customer_id_type})


        if int(frappe.__version__.split('.')[0]) == 13:
            address = frappe.get_doc("Address", sales_invoice_doc.customer_address)
        else:
            address = frappe.get_doc("Address", customer_doc.customer_primary_address)

        add_address_to_party(cac_Party, address)

        cac_PartyLegalEntity = create_element(cac_Party, "cac:PartyLegalEntity")
        create_element(cac_PartyLegalEntity, "cbc:RegistrationName", sales_invoice_doc.customer)

        cac_Contact = create_element(cac_Party, "cac:Contact")
        create_element(cac_Contact, "cbc:Telephone", str(address.phone))
        create_element(cac_Contact, "cbc:ElectronicMail", str(address.email_id))

    except Exception as e:
        frappe.throw(f"Error customer data: {str(e)}")

# Create tax totals section
def tax_total(invoice,sales_invoice_doc):
        try:
            taxable_amount = sales_invoice_doc.base_total - sales_invoice_doc.get('base_discount_amount', 0.0)
            cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_TaxAmount = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount", currencyID="MYR")
            tax_amount_without_retention =  taxable_amount * float(sales_invoice_doc.taxes[0].rate) / 100
            cbc_TaxAmount.text=f"{abs(round(tax_amount_without_retention, 2)):.2f}"
           

            cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")
            cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount", currencyID="MYR")
            cbc_TaxableAmount.text = str(abs(round(taxable_amount, 2)))
            cbc_TaxAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount", currencyID="MYR")
            cbc_TaxAmount.text =str(abs(round(taxable_amount * float(sales_invoice_doc.taxes[0].rate) / 100, 2)))

            cac_TaxCategory = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")
            cbc_ID = ET.SubElement(cac_TaxCategory, "cbc:ID")
            cbc_ID.text = str(sales_invoice_doc.custom_zatca_tax_category)
            cbc_Percent = ET.SubElement(cac_TaxCategory, "cbc:Percent")
            cbc_Percent.text =str(sales_invoice_doc.taxes[0].rate)
            cbc_TaxExemptionReason = ET.SubElement(cac_TaxCategory, "cbc:TaxExemptionReason")
            if (sales_invoice_doc.custom_zatca_tax_category) == "E":
                cbc_TaxExemptionReason.text = sales_invoice_doc.custom_exemption_code
            else:
                cbc_TaxExemptionReason.text = "NA"

            cac_TaxScheme = ET.SubElement(cac_TaxCategory, "cac:TaxScheme")
            cbc_TaxScheme_ID = ET.SubElement(cac_TaxScheme, "cbc:ID",  schemeAgencyID="6",schemeID="UN/ECE 5153")
            cbc_TaxScheme_ID.text = "OTH"
        except Exception as e:
                frappe.throw(f"Error tax total: {str(e)}")
     
def tax_total_with_template(invoice, sales_invoice_doc):
    try:
        tax_category_totals = {}

        # Group items by ZATCA tax category and calculate taxable amounts
        for item in sales_invoice_doc.items:
            item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
            zatca_tax_category = item_tax_template.custom_zatca_tax_category

            if zatca_tax_category not in tax_category_totals:
                tax_category_totals[zatca_tax_category] = {
                    "taxable_amount": 0,
                    "tax_amount": 0,
                    "tax_rate": item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 0,
                    "exemption_reason_code": item_tax_template.custom_exemption_reason_code
                }

            if sales_invoice_doc.currency == "SAR":
                tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(item.base_amount)
            else:
                tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(item.amount)

        # Apply discount only once to the first tax category
        first_tax_category = next(iter(tax_category_totals))
        base_discount_amount = sales_invoice_doc.get('discount_amount', 0.0)
        tax_category_totals[first_tax_category]["taxable_amount"] -= base_discount_amount

        # Calculate tax amounts
        for zatca_tax_category in tax_category_totals:
            taxable_amount = tax_category_totals[zatca_tax_category]["taxable_amount"]
            tax_rate = tax_category_totals[zatca_tax_category]["tax_rate"]
            tax_category_totals[zatca_tax_category]["tax_amount"] = abs(
                round(taxable_amount * tax_rate / 100, 2)
            )

        # Calculate total tax
        total_tax = sum(
            totals["tax_amount"] for totals in tax_category_totals.values()
        )
        tax_amount_without_retention_sar = round(abs(total_tax), 2)

        # Add TaxTotal XML element
        cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
        cbc_TaxAmount = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount", currencyID="MYR")
        cbc_TaxAmount.text = str(tax_amount_without_retention_sar)

        # Add TaxSubtotal XML elements for each ZATCA tax category
        for zatca_tax_category, totals in tax_category_totals.items():
            cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")
            cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount", currencyID="MYR")
            cbc_TaxableAmount.text = str(round(totals["taxable_amount"], 2))

            cbc_TaxAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount", currencyID="MYR")
            cbc_TaxAmount.text = str(round(totals["tax_amount"], 2))

            cac_TaxCategory = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")
            cbc_ID = ET.SubElement(cac_TaxCategory, "cbc:ID")
            cbc_ID.text = zatca_tax_category

            cbc_Percent = ET.SubElement(cac_TaxCategory, "cbc:Percent")
            cbc_Percent.text = f"{totals['tax_rate']:.2f}"

            cbc_TaxExemptionReason = ET.SubElement(cac_TaxCategory, "cbc:TaxExemptionReason")
            if zatca_tax_category == "E":
                cbc_TaxExemptionReason.text = item_tax_template.custom_exemption_reason_code
            else:
                cbc_TaxExemptionReason.text = "NA"

            cac_TaxScheme = ET.SubElement(cac_TaxCategory, "cac:TaxScheme")
            cbc_TaxScheme_ID = ET.SubElement(cac_TaxScheme, "cbc:ID", schemeAgencyID="6", schemeID="UN/ECE 5153")
            cbc_TaxScheme_ID.text = "OTH"

    except Exception as e:
        frappe.throw(f"Error in tax total calculation: {str(e)}")


def legal_monetary_total(invoice, sales_invoice_doc):
    try:
    
        discount_amount = sales_invoice_doc.get('discount_amount', 0.0)
        taxable_amount_1 = sales_invoice_doc.total - discount_amount
        tax_amount_without_retention = taxable_amount_1 * (sales_invoice_doc.taxes[0].rate) / 100
        tax_exclusive_amount = abs(taxable_amount_1)
        tax_inclusive_amount = tax_exclusive_amount + abs(round(tax_amount_without_retention, 2))
        payable_amount = tax_inclusive_amount

        cac_LegalMonetaryTotal = create_element(invoice, "cac:LegalMonetaryTotal")
        
        create_element(cac_LegalMonetaryTotal, "cbc:LineExtensionAmount", str(abs(sales_invoice_doc.total)), {"currencyID": "MYR"})
        create_element(cac_LegalMonetaryTotal, "cbc:TaxExclusiveAmount", str(tax_exclusive_amount), {"currencyID": "MYR"})
        create_element(cac_LegalMonetaryTotal, "cbc:TaxInclusiveAmount", str(tax_inclusive_amount), {"currencyID": "MYR"})
        create_element(cac_LegalMonetaryTotal, "cbc:AllowanceTotalAmount", str(abs(discount_amount)), {"currencyID": "MYR"})
        create_element(cac_LegalMonetaryTotal, "cbc:PayableAmount", str(payable_amount), {"currencyID": "MYR"})

    except Exception as e:
        frappe.throw(f"Error legal monetary: {str(e)}")

def get_Tax_for_Item(full_string,item):
                    try:                                          
                        data = json.loads(full_string)
                        tax_percentage=data.get(item,[0,0])[0]
                        tax_amount = data.get(item, [0, 0])[1]
                        return tax_amount,tax_percentage
                    except Exception as e:
                            frappe.throw("error occured in tax for item"+ str(e) )

def invoice_line_item(invoice, sales_invoice_doc):
    try:
        for single_item in sales_invoice_doc.items:
            cac_InvoiceLine = ET.SubElement(invoice, "cac:InvoiceLine")
            cbc_ID = ET.SubElement(cac_InvoiceLine, "cbc:ID")
            cbc_ID.text = str(single_item.idx)
            cbc_InvoicedQuantity = ET.SubElement(cac_InvoiceLine, "cbc:InvoicedQuantity", unitCode="H87")
            cbc_InvoicedQuantity.text = str(abs(single_item.qty))
            cbc_LineExtensionAmount = ET.SubElement(cac_InvoiceLine, "cbc:LineExtensionAmount", currencyID="MYR")
            cbc_LineExtensionAmount.text = str(abs(single_item.amount))

            discount_amount = abs(single_item.get('discount_amount', 0.0))
            if discount_amount > 0:
                cac_AllowanceCharge = ET.SubElement(cac_InvoiceLine, "cac:AllowanceCharge")
                cbc_ChargeIndicator = ET.SubElement(cac_AllowanceCharge, "cbc:ChargeIndicator")
                cbc_ChargeIndicator.text = "false"
                cbc_AllowanceChargeReason = ET.SubElement(cac_AllowanceCharge, "cbc:AllowanceChargeReason")
                cbc_AllowanceChargeReason.text = "Item Discount"
                cbc_MultiplierFactorNumeric = ET.SubElement(cac_AllowanceCharge, "cbc:MultiplierFactorNumeric")
                cbc_MultiplierFactorNumeric.text = "1"
                cbc_Amount = ET.SubElement(cac_AllowanceCharge, "cbc:Amount", currencyID="MYR")
                cbc_Amount.text = str(discount_amount)

           
            cac_TaxTotal = ET.SubElement(cac_InvoiceLine, "cac:TaxTotal")
            cbc_TaxAmount = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount", currencyID="MYR")
            cbc_TaxAmount.text = str(abs(round((sales_invoice_doc.taxes[0].rate) * single_item.amount / 100, 2)))

            cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")
            cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount", currencyID="MYR")
            cbc_TaxableAmount.text = str(abs(single_item.amount - discount_amount))
            cbc_TaxAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount", currencyID="MYR")
            cbc_TaxAmount.text = str(abs(round((sales_invoice_doc.taxes[0].rate) * single_item.amount / 100, 2)))

            cac_TaxCategory = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")
            cbc_ID = ET.SubElement(cac_TaxCategory, "cbc:ID")
            cbc_ID.text = str(sales_invoice_doc.custom_zatca_tax_category)
            cbc_Percent = ET.SubElement(cac_TaxCategory, "cbc:Percent")
            cbc_Percent.text = str(sales_invoice_doc.taxes[0].rate)
            cac_TaxScheme = ET.SubElement(cac_TaxCategory, "cac:TaxScheme")
            cbc_TaxScheme_ID = ET.SubElement(cac_TaxScheme, "cbc:ID", schemeAgencyID="6", schemeID="UN/ECE 5153")
            cbc_TaxScheme_ID.text = "OTH"

            
            cac_Item = ET.SubElement(cac_InvoiceLine, "cac:Item")
            cbc_Description = ET.SubElement(cac_Item, "cbc:Description")
            cbc_Description.text = str(single_item.description)

            cac_CommodityClassification = ET.SubElement(cac_Item, "cac:CommodityClassification")
            cbc_ItemClassificationCode = ET.SubElement(cac_CommodityClassification, "cbc:ItemClassificationCode", listID="CLASS")
            cbc_ItemClassificationCode.text =str(sales_invoice_doc.custom_item_classification_code_)

           
            cac_Price = ET.SubElement(cac_InvoiceLine, "cac:Price")
            cbc_PriceAmount = ET.SubElement(cac_Price, "cbc:PriceAmount", currencyID="MYR")
            cbc_PriceAmount.text = str(abs(single_item.base_price_list_rate) - discount_amount)

            
            cac_ItemPriceExtension = ET.SubElement(cac_InvoiceLine, "cac:ItemPriceExtension")
            cbc_Amount = ET.SubElement(cac_ItemPriceExtension, "cbc:Amount", currencyID="MYR")
            cbc_Amount.text = str(abs(single_item.base_amount))

    except Exception as e:
        frappe.throw(f"Error in invoice_line: {str(e)}")

def item_data_with_template(invoice,sales_invoice_doc):
       
    try:
        for single_item in sales_invoice_doc.items:
            item_tax_template = frappe.get_doc('Item Tax Template', single_item.item_tax_template)
            item_tax_percentage = item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 0
            cac_InvoiceLine = ET.SubElement(invoice, "cac:InvoiceLine")
            cbc_ID = ET.SubElement(cac_InvoiceLine, "cbc:ID")
            cbc_ID.text = str(single_item.idx)
            cbc_InvoicedQuantity = ET.SubElement(cac_InvoiceLine, "cbc:InvoicedQuantity", unitCode="H87")
            cbc_InvoicedQuantity.text = str(abs(single_item.qty))
            cbc_LineExtensionAmount = ET.SubElement(cac_InvoiceLine, "cbc:LineExtensionAmount", currencyID="MYR")
            cbc_LineExtensionAmount.text = str(abs(single_item.amount))

            discount_amount = abs(single_item.get('discount_amount', 0.0))
            if discount_amount > 0:
                cac_AllowanceCharge = ET.SubElement(cac_InvoiceLine, "cac:AllowanceCharge")
                cbc_ChargeIndicator = ET.SubElement(cac_AllowanceCharge, "cbc:ChargeIndicator")
                cbc_ChargeIndicator.text = "false"
                cbc_AllowanceChargeReason = ET.SubElement(cac_AllowanceCharge, "cbc:AllowanceChargeReason")
                cbc_AllowanceChargeReason.text = "Item Discount"
                cbc_MultiplierFactorNumeric = ET.SubElement(cac_AllowanceCharge, "cbc:MultiplierFactorNumeric")
                cbc_MultiplierFactorNumeric.text = "1"
                cbc_Amount = ET.SubElement(cac_AllowanceCharge, "cbc:Amount", currencyID="MYR")
                cbc_Amount.text = str(discount_amount)

            
            cac_TaxTotal = ET.SubElement(cac_InvoiceLine, "cac:TaxTotal")
            cbc_TaxAmount = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount", currencyID="MYR")
            cbc_TaxAmount.text =  str(abs(round(item_tax_percentage * single_item.amount / 100, 2)))

            cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")
            cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount", currencyID="MYR")
            cbc_TaxableAmount.text = str(abs(single_item.amount - discount_amount))
            cbc_TaxAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount", currencyID="MYR")
            cbc_TaxAmount.text =  str(abs(round(item_tax_percentage * single_item.amount / 100, 2)))

            zatca_tax_category = item_tax_template.custom_zatca_tax_category
            cac_TaxCategory = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")
            cbc_ID = ET.SubElement(cac_TaxCategory, "cbc:ID")
            cbc_ID.text = str(zatca_tax_category)
            cbc_Percent = ET.SubElement(cac_TaxCategory, "cbc:Percent")
            cbc_Percent.text = f"{float(item_tax_percentage):.2f}"
            cac_TaxScheme = ET.SubElement(cac_TaxCategory, "cac:TaxScheme")
            cbc_TaxScheme_ID = ET.SubElement(cac_TaxScheme, "cbc:ID", schemeAgencyID="6", schemeID="UN/ECE 5153")
            cbc_TaxScheme_ID.text = "OTH"

            cac_Item = ET.SubElement(cac_InvoiceLine, "cac:Item")
            cbc_Description = ET.SubElement(cac_Item, "cbc:Description")
            cbc_Description.text = str(single_item.description)

            cac_CommodityClassification = ET.SubElement(cac_Item, "cac:CommodityClassification")
            cbc_ItemClassificationCode = ET.SubElement(cac_CommodityClassification, "cbc:ItemClassificationCode", listID="CLASS")
            cbc_ItemClassificationCode.text =str(sales_invoice_doc.custom_item_classification_code_)

            cac_Price = ET.SubElement(cac_InvoiceLine, "cac:Price")
            cbc_PriceAmount = ET.SubElement(cac_Price, "cbc:PriceAmount", currencyID="MYR")
            cbc_PriceAmount.text = str(abs(single_item.base_price_list_rate) - discount_amount)

            cac_ItemPriceExtension = ET.SubElement(cac_InvoiceLine, "cac:ItemPriceExtension")
            cbc_Amount = ET.SubElement(cac_ItemPriceExtension, "cbc:Amount", currencyID="MYR")
            cbc_Amount.text = str(abs(single_item.base_amount))

    except Exception as e:
        frappe.throw(f"Error in invoice_line: {str(e)}")




def xml_structuring(invoice,sales_invoice_doc):
  
    raw_xml = ET.tostring(invoice, encoding='utf-8', method='xml').decode('utf-8')
    with open(frappe.local.site + "/private/files/create.xml", 'w') as file:
        file.write(raw_xml)
    try:
                    fileXx = frappe.get_doc(
                        {   "doctype": "File",        
                            "file_type": "xml",  
                            "file_name":  "E-invoice-" + sales_invoice_doc.name + ".xml",
                            "attached_to_doctype":sales_invoice_doc.doctype,
                            "attached_to_name":sales_invoice_doc.name, 
                            "content": raw_xml,
                            "is_private": 1,})
                    fileXx.save()


    except Exception as e:
                    frappe.throw(frappe.get_traceback())
    return raw_xml



