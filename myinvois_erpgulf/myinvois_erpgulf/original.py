"""the original file defines the integration setup of signing of the invoice and
 submission of the invoice to the LHDN Malaysia"""

import hashlib
import base64
import datetime
import json
import xml.dom.minidom as minidom
import frappe
import requests
from lxml import etree
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives.serialization import (
    pkcs12,
    Encoding,
    BestAvailableEncryption,
    PrivateFormat,
)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from myinvois_erpgulf.myinvois_erpgulf.createxml import (
    create_invoice_with_extensions,
    salesinvoice_data,
    company_data,
    customer_data,
    delivery_data,
    tax_total,
    legal_monetary_total,
    xml_structuring,
    invoice_line_item,
    item_data_with_template,
    tax_total_with_template,
    get_icv_code,
    payment_data,
    allowance_charge_data,
    generate_qr_code,
    attach_qr_code_to_sales_invoice,
)
from myinvois_erpgulf.myinvois_erpgulf.taxpayerlogin import get_access_token


def xml_hash():
    """defining the xml hash"""
    try:
        with open(frappe.local.site + "/private/files/create.xml", "rb") as file:
            xml_content = file.read()
        root = etree.fromstring(xml_content)
        line_xml = etree.tostring(root, pretty_print=False, encoding="UTF-8")
        sha256_hash = hashlib.sha256(line_xml).digest()
        doc_hash = base64.b64encode(sha256_hash).decode("utf-8")
        return line_xml, doc_hash
    except (OSError, etree.XMLSyntaxError, base64.binascii.Error) as e:
        frappe.throw(f"Error in xml hash: {str(e)}")


def certificate_data():
    """defining the certificate data"""
    try:

        settings = frappe.get_doc("LHDN Malaysia Setting")
        attached_file = settings.certificate_file

        if not attached_file:
            frappe.throw("No PFX file attached in the settings.")
        file_doc = frappe.get_doc("File", {"file_url": attached_file})
        pfx_path = file_doc.get_full_path()

        pfx_password = settings.pfx_cert_password
        pem_output_path = frappe.local.site + "/private/files/certificate.pem"
        pem_encryption_password = pfx_password.encode()
        with open(pfx_path, "rb") as f:
            pfx_data = f.read()
        private_key, certificate, additional_certificates = (
            pkcs12.load_key_and_certificates(
                pfx_data, pfx_password.encode(), backend=default_backend()
            )
        )

        with open(pem_output_path, "wb") as pem_file:
            if private_key:
                pem_file.write(
                    private_key.private_bytes(
                        encoding=Encoding.PEM,
                        format=PrivateFormat.PKCS8,
                        encryption_algorithm=BestAvailableEncryption(
                            pem_encryption_password
                        ),
                    )
                )

            if certificate:
                certificate_base64 = base64.b64encode(
                    certificate.public_bytes(Encoding.DER)
                ).decode("utf-8")
                pem_file.write(certificate.public_bytes(Encoding.PEM))
                x509_issuer_name = formatted_issuer_name = (
                    certificate.issuer.rfc4514_string()
                )
                formatted_issuer_name = x509_issuer_name.replace(",", ", ")
                x509_serial_number = certificate.serial_number
                cert_digest = base64.b64encode(
                    certificate.fingerprint(hashes.SHA256())
                ).decode("utf-8")
                signing_time = datetime.datetime.now(datetime.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )

            if additional_certificates:
                for cert in additional_certificates:
                    pem_file.write(cert.public_bytes(Encoding.PEM))
            return (
                certificate_base64,
                formatted_issuer_name,
                x509_serial_number,
                cert_digest,
                signing_time,
            )

    except (frappe.DoesNotExistError, OSError, ValueError) as e:
        frappe.throw(f"Error loading certificate details: {str(e)}")


def bytes_to_base64_string(value: bytes) -> str:
    """
    Convert a bytes object to a base64 encoded ASCII string.
    """
    return base64.b64encode(value).decode("ASCII")


def sign_data(line_xml):
    """defining the sign data"""
    try:
        # print(single_line_ xml1)
        hashdata = line_xml.decode().encode()
        f = open(
            frappe.local.site + "/private/files/certificate.pem", "r", encoding="utf-8"
        )
        cert_pem = f.read()
        if hashdata is None:
            raise ValueError("hashdata cannot be None")
        if cert_pem is None:
            raise ValueError("cert_pem cannot be None")
        cert = load_pem_x509_certificate(cert_pem.encode(), default_backend())
        # print(cert.issuer)
        settings = frappe.get_doc("LHDN Malaysia Setting")
        pass_file = settings.pfx_cert_password
        private_key = serialization.load_pem_private_key(
            cert_pem.encode(),
            password=pass_file.encode(),
        )

        if private_key is None or not isinstance(private_key, rsa.RSAPrivateKey):
            raise ValueError("The certificate does not contain an RSA private key.")

        try:
            signed_data = private_key.sign(
                hashdata, padding.PKCS1v15(), hashes.SHA256()
            )
            base64_bytes = base64.b64encode(signed_data)
            base64_string = base64_bytes.decode("ascii")
            # print(f"Encoded string: {base64_string}")
        except (ValueError, TypeError) as e:
            frappe.throw(f"An error occurred while signing the data.: {str(e)}")

        return base64_string
    except (ValueError, TypeError) as e:
        frappe.throw(f"Error in sign data: {str(e)}")


def signed_properties_hash(
    signing_time, cert_digest, formatted_issuer_name, x509_serial_number
):
    """defining the signed properties hash"""
    try:

        single_line_xml = f"""<xades:SignedProperties Id="id-xades-signed-props" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#"><xades:SignedSignatureProperties><xades:SigningTime>{signing_time}</xades:SigningTime><xades:SigningCertificate><xades:Cert><xades:CertDigest><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256" xmlns:ds="http://www.w3.org/2000/09/xmldsig#"></ds:DigestMethod><ds:DigestValue xmlns:ds="http://www.w3.org/2000/09/xmldsig#">{cert_digest}</ds:DigestValue></xades:CertDigest><xades:IssuerSerial><ds:X509IssuerName xmlns:ds="http://www.w3.org/2000/09/xmldsig#">{formatted_issuer_name}</ds:X509IssuerName><ds:X509SerialNumber xmlns:ds="http://www.w3.org/2000/09/xmldsig#">{x509_serial_number}</ds:X509SerialNumber></xades:IssuerSerial></xades:Cert></xades:SigningCertificate></xades:SignedSignatureProperties></xades:SignedProperties>"""
        prop_cert_hash = hashlib.sha256(single_line_xml.encode("utf-8")).digest()
        prop_cert_base64 = base64.b64encode(prop_cert_hash).decode("utf-8")
        # print(f"SHA-256 Hash in Base64 (propCert): {prop_cert_base64}")
        return prop_cert_base64
    except (ValueError, TypeError) as e:
        frappe.throw(f"Error signed properties hash: {str(e)}")


def ubl_extension_string(
    doc_hash,
    prop_cert_base64,
    signature,
    certificate_base64,
    signing_time,
    cert_digest,
    formatted_issuer_name,
    x509_serial_number,
    line_xml,
):
    """defining the ubl extension string"""
    try:
        inv_xml_string = f"""<ext:UBLExtensions>
                        <ext:UBLExtension>
                            <ext:ExtensionURI>urn:oasis:names:specification:ubl:dsig:enveloped:xades</ext:ExtensionURI>
                            <ext:ExtensionContent>
                                <sig:UBLDocumentSignatures xmlns:sac="urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2"
                                     xmlns:sbc="urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2"
                                     xmlns:sig="urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2">
                                    <sac:SignatureInformation>
                                        <cbc:ID>urn:oasis:names:specification:ubl:signature:1</cbc:ID>
                                        <sbc:ReferencedSignatureID>urn:oasis:names:specification:ubl:signature:Invoice</sbc:ReferencedSignatureID>
                                        <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="signature">
                                            <ds:SignedInfo>
                                                <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2006/12/xml-c14n11"></ds:CanonicalizationMethod>
                                                <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"></ds:SignatureMethod>
                                                <ds:Reference Id="id-doc-signed-data" URI="">
                                                    <ds:Transforms>
                                                        <ds:Transform Algorithm="http://www.w3.org/TR/1999/REC-xpath-19991116">
                                                            <ds:XPath>not(//ancestor-or-self::ext:UBLExtensions)</ds:XPath>
                                                        </ds:Transform>
                                                        <ds:Transform Algorithm="http://www.w3.org/TR/1999/REC-xpath-19991116">
                                                            <ds:XPath>not(//ancestor-or-self::cac:Signature)</ds:XPath>
                                                        </ds:Transform>
                                                        <ds:Transform Algorithm="http://www.w3.org/2006/12/xml-c14n11"></ds:Transform>
                                                    </ds:Transforms>
                                                    <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"></ds:DigestMethod>
                                                    <ds:DigestValue>{doc_hash}</ds:DigestValue>
                                                </ds:Reference>
                                                <ds:Reference Type="http://www.w3.org/2000/09/xmldsig#SignatureProperties" URI="#id-xades-signed-props">
                                                    <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"></ds:DigestMethod>
                                                    <ds:DigestValue>{prop_cert_base64}</ds:DigestValue>
                                                </ds:Reference>
                                            </ds:SignedInfo>
                                            <ds:SignatureValue>{signature}</ds:SignatureValue>
                                            <ds:KeyInfo>
                                                <ds:X509Data>
                                                    <ds:X509Certificate>{certificate_base64}</ds:X509Certificate>
                                                </ds:X509Data>
                                            </ds:KeyInfo>
                                            <ds:Object>
                                                <xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Target="signature">
                                                    <xades:SignedProperties Id="id-xades-signed-props">
                                                        <xades:SignedSignatureProperties>
                                                            <xades:SigningTime>{signing_time}</xades:SigningTime>
                                                            <xades:SigningCertificate>
                                                                <xades:Cert>
                                                                    <xades:CertDigest>
                                                                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"></ds:DigestMethod>
                                                                        <ds:DigestValue>{cert_digest}</ds:DigestValue>
                                                                    </xades:CertDigest>
                                                                    <xades:IssuerSerial>
                                                                        <ds:X509IssuerName>{formatted_issuer_name}</ds:X509IssuerName>
                                                                        <ds:X509SerialNumber>{x509_serial_number}</ds:X509SerialNumber>
                                                                    </xades:IssuerSerial>
                                                                </xades:Cert>
                                                            </xades:SigningCertificate>
                                                        </xades:SignedSignatureProperties>
                                                    </xades:SignedProperties>
                                                </xades:QualifyingProperties>
                                            </ds:Object>
                                        </ds:Signature>
                                    </sac:SignatureInformation>
                                </sig:UBLDocumentSignatures>
                            </ext:ExtensionContent>
                        </ext:UBLExtension>
                    </ext:UBLExtensions>"""
        inv_xml_string_single_line = (
            inv_xml_string.replace("\n", "").replace("  ", "").replace("> <", "><")
        )
        string = line_xml.decode()
        result = ""
        if isinstance(string, str) and isinstance(inv_xml_string_single_line, str):

            insert_position = string.find(">") + 1
            result = (
                string[:insert_position]
                + inv_xml_string_single_line
                + string[insert_position:]
            )

        signature_string = """<cac:Signature><cbc:ID>urn:oasis:names:specification:ubl:signature:Invoice</cbc:ID><cbc:SignatureMethod>urn:oasis:names:specification:ubl:dsig:enveloped:xades</cbc:SignatureMethod></cac:Signature>"""
        insert_position = result.find("<cac:AccountingSupplierParty>")
        if insert_position != -1:

            result_final = (
                result[:insert_position] + signature_string + result[insert_position:]
            )
            # print(result_final)

            output_path = frappe.local.site + "/private/files/output.xml"
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(result_final)

            # frappe.throw("The modified XML has been saved to 'signedxml_for_submit.xml'.")
        else:
            frappe.throw(
                "The element <cac:AccountingSupplierParty> was not found in the XML string."
            )
    except (ValueError, TypeError, OSError) as e:
        frappe.throw(f"Error ubl extension string: {str(e)}")


def submission_url(sales_invoice_doc):
    """defining the submission url"""
    try:
        settings = frappe.get_doc("LHDN Malaysia Setting")
        token = settings.bearer_token  # Fetch token from settings

        # Determine the file path based on integration type
        file_path = (
            "/private/files/output.xml"
            if settings.integration_type == "Production"
            else "/private/files/create.xml"
        )
        xml_path = frappe.local.site + file_path

        # Read XML data
        with open(xml_path, "rb") as file:
            xml_data = file.read()

        # Calculate hash and encode XML
        sha256_hash = hashlib.sha256(xml_data).hexdigest()
        encoded_xml = base64.b64encode(xml_data).decode("utf-8")
        invoice_number = sales_invoice_doc.name

        json_payload = {
            "documents": [
                {
                    "format": "XML",
                    "documentHash": sha256_hash,
                    "codeNumber": get_icv_code(invoice_number),
                    "document": encoded_xml,
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Function to send the submission request
        def submit_request():
            return requests.post(
                "https://preprod-api.myinvois.hasil.gov.my/api/v1.0/documentsubmissions",
                headers=headers,
                json=json_payload,
                timeout=30,
            )

        # Initial submission
        response = submit_request()

        # If unauthorized, refresh token and retry
        if response.status_code == 401:
            # frappe.msgprint("Unauthorized: Refreshing access token...")
            get_access_token()  # Refresh the token and save it in settings
            settings.reload()  # Reload settings to get the new token
            token = settings.bearer_token  # Fetch updated token
            headers["Authorization"] = f"Bearer {token}"
            response = submit_request()

        # Handle response
        # if response.status_code != 200:
        #     frappe.throw(f"Submission failed: {response.text}")
        frappe.msgprint(f"Response body: {response.text}")
        response_data = response.json()
        status = "Approved" if response_data.get("submissionUid") else "Rejected"
        sales_invoice_doc.db_set("custom_submit_response", response.text)
        existing_files = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": sales_invoice_doc.doctype,
                "attached_to_name": sales_invoice_doc.name,
            },
            fields=["name", "file_name"],
        )
        for file in existing_files:
            if file["file_name"].endswith(".xml") or file["file_name"].endswith(
                ".png"
            ):  # Check if XML or QR file
                frappe.delete_doc("File", file["name"], ignore_permissions=True)
        # Format and save the XML
        pretty_xml_string = minidom.parseString(xml_data).toprettyxml(indent="  ")
        file_name = (
            f"Submitted-{sales_invoice_doc.name}.xml"
            if settings.integration_type == "Production"
            else f"E-invoice-{sales_invoice_doc.name}.xml"
        )

        xml_file = frappe.get_doc(
            {
                "doctype": "File",
                "file_type": "xml",
                "file_name": file_name,
                "attached_to_doctype": sales_invoice_doc.doctype,
                "attached_to_name": sales_invoice_doc.name,
                "content": pretty_xml_string,
                "is_private": 1,
            }
        )
        xml_file.save()

        # Generate and attach QR code
        qr_image_path = generate_qr_code(sales_invoice_doc, status)
        attach_qr_code_to_sales_invoice(sales_invoice_doc, qr_image_path)

    except FileNotFoundError as e:
        frappe.throw(f"File not found: {e}")
    except requests.RequestException as e:
        frappe.throw(f"API request failed: {e}")
    except (FileNotFoundError, requests.RequestException, ValueError, KeyError) as e:
        frappe.throw(f"Error in submission URL: {str(e)}")


def success_log(response, submission_uuid, status, invoice_number):
    """Log successful invoice submissions or update an existing log."""
    try:
        current_time = frappe.utils.now()
        response_str = (
            json.dumps(response, indent=4)
            if isinstance(response, dict)
            else str(response)
        )

        # Check if a document with the same invoice_number already exists
        existing_doc = frappe.db.exists(
            "LHDN Success Log", {"invoice_number": invoice_number}
        )
        if existing_doc:
            # Update the existing document
            doc_instance = frappe.get_doc("LHDN Success Log", existing_doc)
            doc_instance.update(
                {
                    "custom_status_of_submisison": status,
                    "submission_uuid": submission_uuid,
                    "lhdn_response": response_str,
                    "time": current_time,
                }
            )
            frappe.log(f"Updated LHDN Success Log: {invoice_number}")
        else:
            # Create a new document
            doc_instance = frappe.get_doc(
                {
                    "doctype": "LHDN Success Log",
                    "title": "LHDN Invoice Submission Successful",
                    "message": "Message from LHDN",
                    "custom_status_of_submisison": status,
                    "submission_uuid": submission_uuid,
                    "invoice_number": invoice_number,
                    "time": current_time,
                    "lhdn_response": response_str,
                }
            )
            doc_instance.insert(ignore_permissions=True)
            frappe.log(f"Created new LHDN Success Log: {invoice_number}")

        # Save the document (necessary if updated)
        doc_instance.save(ignore_permissions=True)
        return doc_instance

    except Exception as e:
        frappe.log_error(f"Error in success_log: {str(e)}")
        frappe.throw(f"Error in success log: {str(e)}")


def error_log(custom_error_submission=None):
    """
    Logs errors during LHDN invoice submission.
    Includes full traceback and optional custom submission details.
    """
    try:
        # Capture the full traceback of the error
        error_message = frappe.get_traceback()
        frappe.log(f"Captured error traceback: {error_message}")

        # Create a new error log document
        error_doc = frappe.get_doc(
            {
                "doctype": "LHDN Error Log",
                "title": "LHDN INVOICE SUBMISSION Failed",
                "error": error_message,
            }
        )

        # Save the error log
        error_doc.insert(ignore_permissions=True)

        # Log a success message in the server logs
        frappe.log(
            f"Error logged successfully with custom details: {custom_error_submission}"
        )

    except Exception as e:
        # If logging fails, log the exception and throw a descriptive message
        frappe.log_error(f"Failed to log error: {frappe.get_traceback()}")
        frappe.throw(f"Error while logging the error: {str(e)}")


def status_submission(invoice_number, sales_invoice_doc):
    """Fetching the status of the submission"""
    try:
        settings = frappe.get_doc("LHDN Malaysia Setting")
        token = settings.bearer_token
        response_data = json.loads(
            sales_invoice_doc.custom_submit_response
        )  # Parse JSON response
        submission_uid = response_data.get("submissionUid")

        if not submission_uid:
            frappe.throw("Submission UID not found in the response.")

        # Format the URL correctly
        url = f"https://preprod-api.myinvois.hasil.gov.my/api/v1.0/documentsubmissions/{submission_uid}"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            response_data = response.json()  # Parse the response as JSON
            document_summary = response_data.get("documentSummary", [])
            if document_summary:
                status = document_summary[0].get("status", "Unknown")
                sales_invoice_doc.custom_lhdn_status = status
                sales_invoice_doc.save(ignore_permissions=True)
            doc = success_log(
                response.json(), submission_uid, status, invoice_number
            )  # Pass JSON, not string

            doc.save(ignore_permissions=True)

        else:
            error_log()
    except Exception as e:
        frappe.log_error(f"Error during status submission: {str(e)}")
        frappe.throw(f"Error during status submission: {str(e)}")


@frappe.whitelist(allow_guest=True)
def status_submit_success_log(doc):
    """Defining the status submit success log"""

    try:
        # Load the document into a Python dictionary if passed as a string
        if isinstance(doc, str):
            doc = frappe.parse_json(doc)

        settings = frappe.get_doc("LHDN Malaysia Setting")
        token = settings.bearer_token
        submission_uid = doc.get("submission_uuid")
        if not submission_uid:
            frappe.throw("Submission UID is missing from the document.")

        url = f"https://preprod-api.myinvois.hasil.gov.my/api/v1.0/documentsubmissions/{submission_uid}"

        headers = {"Authorization": f"Bearer {token}"}  # Authorization header

        response = requests.get(url, headers=headers, timeout=30)  # Send the request
        if response.status_code == 401:
            get_access_token()  # Assuming this function refreshes the token
            settings.reload()  # Reload settings to get the updated token
            token = settings.bearer_token  # Get the refreshed token
            headers["Authorization"] = f"Bearer {token}"

            # Retry the request with the new token
            response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            response_data = response.json()
            doc_instance = frappe.get_doc("LHDN Success Log", doc.get("name"))
            document_summary = response_data.get("documentSummary", [])
            if document_summary:
                status = document_summary[0].get("status", "Unknown")
                doc_instance.custom_status_of_submisison = status
            # Get the actual doc instance
            doc_instance.lhdn_response = json.dumps(
                response_data, indent=4
            )  # Update the lhdn_response field
            doc_instance.time = frappe.utils.now()
            doc_instance.save(ignore_permissions=True)

            return {"message": "Response saved successfully"}

        else:

            response_data = response.json()
            doc_instance = frappe.get_doc("LHDN Success Log", doc.get("name"))
            doc_instance.lhdn_response = json.dumps(response_data, indent=4)
            doc_instance.save(ignore_permissions=True)

    except requests.RequestException as e:
        frappe.throw(f"Request failed: {str(e)}")
        frappe.log_error(f"Error during status submission: {str(e)}")
    except (ValueError, KeyError, frappe.ValidationError) as e:
        frappe.log_error(f"Error during status submission: {str(e)}")


@frappe.whitelist(allow_guest=True)
def submit_document(invoice_number, any_item_has_tax_template=False):
    """defining the submit document"""
    try:
        sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)

        # Check if any item has a tax template but not all items have one
        if any(item.item_tax_template for item in sales_invoice_doc.items) and not all(
            item.item_tax_template for item in sales_invoice_doc.items
        ):
            frappe.throw(
                "If any one item has an Item Tax Template, all items must have an Item Tax Template."
            )
        else:
            # Set to True if all items have a tax template
            any_item_has_tax_template = all(
                item.item_tax_template for item in sales_invoice_doc.items
            )

        invoice = create_invoice_with_extensions()
        salesinvoice_data(invoice, sales_invoice_doc)

        company_data(invoice, sales_invoice_doc)
        customer_data(invoice, sales_invoice_doc)
        delivery_data(invoice, sales_invoice_doc)
        payment_data(invoice, sales_invoice_doc)
        # Call appropriate tax total function
        allowance_charge_data(invoice, sales_invoice_doc)
        if not any_item_has_tax_template:
            tax_total(invoice, sales_invoice_doc)
        else:
            tax_total_with_template(invoice, sales_invoice_doc)

        legal_monetary_total(invoice, sales_invoice_doc)

        # Call appropriate item data function
        if not any_item_has_tax_template:
            invoice_line_item(invoice, sales_invoice_doc)
        else:
            item_data_with_template(invoice, sales_invoice_doc)

        xml_structuring(invoice, sales_invoice_doc)

        line_xml, doc_hash = xml_hash()
        settings = frappe.get_doc("LHDN Malaysia Setting")
        if settings.integration_type == "Production":
            (
                certificate_base64,
                formatted_issuer_name,
                x509_serial_number,
                cert_digest,
                signing_time,
            ) = certificate_data()

            signature = sign_data(line_xml)
            prop_cert_base64 = signed_properties_hash(
                signing_time, cert_digest, formatted_issuer_name, x509_serial_number
            )

            ubl_extension_string(
                doc_hash,
                prop_cert_base64,
                signature,
                certificate_base64,
                signing_time,
                cert_digest,
                formatted_issuer_name,
                x509_serial_number,
                line_xml,
            )

        submission_url(sales_invoice_doc)
        status_submission(invoice_number, sales_invoice_doc)

    except (
        frappe.DoesNotExistError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        frappe.ValidationError,
    ) as e:
        frappe.throw(f"Error in submit document: {str(e)}")
