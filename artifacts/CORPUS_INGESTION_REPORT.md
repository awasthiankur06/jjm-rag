# CORPUS INGESTION REPORT

## A. Corpus accounting

- total files found: 45
- total files successfully inspected: 45
- files by extension:
  - .xls: 42
  - .pdf: 3
- files by detected format:
  - html_table: 41
  - pdf: 3
  - text_with_commas: 1
- files by family:
  - report: 18
  - progress/status/coverage: 23
  - unknown: 1
  - sanction/orders: 1
  - guidance: 2

All files are listed in `artifacts/corpus_manifest.json`.

## B. Actual format findings
- AssamDistrict wise number of Rural Population as on (01.xls: detected_format=html_table; extension=.xls; warnings=[]
- CS1 A. Coverage.xls: detected_format=html_table; extension=.xls; warnings=[]
- CS1 B (ii). Robust chlorination system_ Disinfecti.xls: detected_format=html_table; extension=.xls; warnings=[]
- CS1 B(i). Water Quality.xls: detected_format=html_table; extension=.xls; warnings=[]
- District wise number of Rural Population as on (01 (1).xls: detected_format=html_table; extension=.xls; warnings=[]
- District wise number of Rural Population as on (01 (2).xls: detected_format=html_table; extension=.xls; warnings=[]
- District wise number of Rural Population as on (01.xls: detected_format=html_table; extension=.xls; warnings=[]
- FHTCDataTable.pdf: detected_format=pdf; extension=.pdf; warnings=[]
- Format - F27 Status of Pipe Water Supply in Ashram.xls: detected_format=html_table; extension=.xls; warnings=[]
- Format B1- Basic Habitation Information As On 01_0.xls: detected_format=html_table; extension=.xls; warnings=[]
- Format B15 _ Piped water supply schemes.xls: detected_format=html_table; extension=.xls; warnings=[]
- Format C17 A- No Of Quality Affected Habitations & (1).xls: detected_format=html_table; extension=.xls; warnings=[]
- Format C17 A- No Of Quality Affected Habitations & (2).xls: detected_format=html_table; extension=.xls; warnings=[]
- Format C17 A- No Of Quality Affected Habitations & (3).xls: detected_format=html_table; extension=.xls; warnings=[]
- Format C17 A- No Of Quality Affected Habitations &.xls: detected_format=html_table; extension=.xls; warnings=[]
- Format D5- List of Sanction Order.xls: detected_format=html_table; extension=.xls; warnings=[]
- Format WQ1. PWS Infra and Delivery Point (Water Supply Scheme Source).xls: detected_format=html_table; extension=.xls; warnings=[]
- Format WQ2. Remedial Action.xls: detected_format=html_table; extension=.xls; warnings=[]
- Habitation wise FHTC Coverage( Reported Till 23_08.xls: detected_format=html_table; extension=.xls; warnings=[]
- JJM Benchmark - State-wise Implementation in terms.xls: detected_format=html_table; extension=.xls; warnings=[]
- JJM Benchmark – Status of Scheme Planning and Cost.xls: detected_format=html_table; extension=.xls; warnings=[]
- JJM_Operational_Guidelines.pdf: detected_format=pdf; extension=.pdf; warnings=[]
- National Wash Expert Wise Field Visit Report.xls: detected_format=html_table; extension=.xls; warnings=[]
- Operational-Guidelines-JJM-2.pdf: detected_format=pdf; extension=.pdf; warnings=[]
- Progress at district level.xls: detected_format=html_table; extension=.xls; warnings=[]
- Progress in Aspirational districts.xls: detected_format=html_table; extension=.xls; warnings=[]
- Progress in JE_AES districts.xls: detected_format=html_table; extension=.xls; warnings=[]
- Progress tracker of verification of schemes (1).xls: detected_format=html_table; extension=.xls; warnings=[]
- Progress tracker of verification of schemes (2).xls: detected_format=html_table; extension=.xls; warnings=[]
- Progress tracker of verification of schemes (3).xls: detected_format=html_table; extension=.xls; warnings=[]
- Progress tracker of verification of schemes.xls: detected_format=html_table; extension=.xls; warnings=[]
- State wise Allocation Release Expenditure.xls: detected_format=html_table; extension=.xls; warnings=[]
- State wise PWS and FHTC Coverage.xls: detected_format=html_table; extension=.xls; warnings=[]
- State wise number of Rural Population as on (01_04.xls: detected_format=html_table; extension=.xls; warnings=[]
- Status of PWS schemes.xls: detected_format=html_table; extension=.xls; warnings=[]
- Status of Pipe Water Supply in School (1).xls: detected_format=html_table; extension=.xls; warnings=[]
- Status of Pipe Water Supply in School (2).xls: detected_format=text_with_commas; extension=.xls; warnings=[]
- Status of Pipe Water Supply in School (3).xls: detected_format=html_table; extension=.xls; warnings=[]
- Status of Pipe Water Supply in School.xls: detected_format=html_table; extension=.xls; warnings=[]
- Status of geo-tagged water sources.xls: detected_format=html_table; extension=.xls; warnings=[]
- Status of user in JJM field user application.xls: detected_format=html_table; extension=.xls; warnings=[]
- Status of verification of beneficiary provided wit (1).xls: detected_format=html_table; extension=.xls; warnings=[]
- Status of verification of beneficiary provided wit (2).xls: detected_format=html_table; extension=.xls; warnings=[]
- Status of verification of beneficiary provided wit (3).xls: detected_format=html_table; extension=.xls; warnings=[]
- Status of verification of beneficiary provided wit.xls: detected_format=html_table; extension=.xls; warnings=[]

## C. PDF extraction
- FHTCDataTable.pdf: pages=2; extraction_status=text_extracted; probable_table_lines=0; warnings=[]
- JJM_Operational_Guidelines.pdf: pages=132; extraction_status=text_extracted; probable_table_lines=2; warnings=[]
- Operational-Guidelines-JJM-2.pdf: pages=200; extraction_status=no_text_extracted; probable_table_lines=0; warnings=[]

## D. Spreadsheet/table extraction
- AssamDistrict wise number of Rural Population as on (01.xls: format=html_table; tables=1; tables_details=[{'rows': 39, 'cols': 6, 'header_rows': 2}]; title=District wise number of Rural Population as on (01/04/2026); geo=['State', 'District']; warnings=[]
- CS1 A. Coverage.xls: format=html_table; tables=1; tables_details=[{'rows': 38, 'cols': 8, 'header_rows': 4}]; title=CS1 A. Coverage; geo=['State']; warnings=[]
- CS1 B (ii). Robust chlorination system_ Disinfecti.xls: format=html_table; tables=1; tables_details=[{'rows': 39, 'cols': 14, 'header_rows': 5}]; title=CS1 B (ii). Robust chlorination system/ Disinfection system; geo=['State']; warnings=[]
- CS1 B(i). Water Quality.xls: format=html_table; tables=1; tables_details=[{'rows': 38, 'cols': 14, 'header_rows': 4}]; title=CS1 B(i). Water Quality; geo=['State', 'District']; warnings=[]
- District wise number of Rural Population as on (01 (1).xls: format=html_table; tables=1; tables_details=[{'rows': 38, 'cols': 6, 'header_rows': 2}]; title=District wise number of Rural Population as on (01/04/2026); geo=['State', 'District']; warnings=[]
- District wise number of Rural Population as on (01 (2).xls: format=html_table; tables=1; tables_details=[{'rows': 41, 'cols': 6, 'header_rows': 2}]; title=District wise number of Rural Population as on (01/04/2026); geo=['State', 'District']; warnings=[]
- District wise number of Rural Population as on (01.xls: format=html_table; tables=1; tables_details=[{'rows': 17, 'cols': 6, 'header_rows': 2}]; title=District wise number of Rural Population as on (01/04/2026); geo=['State', 'District']; warnings=[]
- Format - F27 Status of Pipe Water Supply in Ashram.xls: format=html_table; tables=1; tables_details=[{'rows': 39, 'cols': 18, 'header_rows': 5}]; title=Format - F27 Status of Pipe Water Supply in Ashram Shala & Other Public Institutions; geo=['State']; warnings=[]
- Format B1- Basic Habitation Information As On 01_0.xls: format=html_table; tables=1; tables_details=[{'rows': 37, 'cols': 9, 'header_rows': 3}]; title=Format B1- Basic Habitation Information As On 01/04/2026; geo=['State', 'District', 'Habitation', 'Block']; warnings=[]
- Format B15 _ Piped water supply schemes.xls: format=html_table; tables=1; tables_details=[{'rows': 37, 'cols': 48, 'header_rows': 5}]; title=Format B15 : Piped water supply schemes; geo=['State', 'Village']; warnings=[]
- Format C17 A- No Of Quality Affected Habitations & (1).xls: format=html_table; tables=1; tables_details=[{'rows': 39, 'cols': 16, 'header_rows': 5}]; title=Format C17 A- No Of Quality Affected Habitations & Population As On 30/08/2026; geo=['State', 'District']; warnings=[]
- Format C17 A- No Of Quality Affected Habitations & (2).xls: format=html_table; tables=1; tables_details=[{'rows': 42, 'cols': 16, 'header_rows': 5}]; title=Format C17 A- No Of Quality Affected Habitations & Population As On 30/08/2026; geo=['State', 'District']; warnings=[]
- Format C17 A- No Of Quality Affected Habitations & (3).xls: format=html_table; tables=1; tables_details=[{'rows': 8, 'cols': 16, 'header_rows': 5}]; title=Format C17 A- No Of Quality Affected Habitations & Population As On 30/08/2026; geo=['State', 'District']; warnings=[]
- Format C17 A- No Of Quality Affected Habitations &.xls: format=html_table; tables=1; tables_details=[{'rows': 40, 'cols': 16, 'header_rows': 5}]; title=Format C17 A- No Of Quality Affected Habitations & Population As On 30/08/2026; geo=['State', 'District']; warnings=[]
- Format D5- List of Sanction Order.xls: format=html_table; tables=1; tables_details=[{'rows': 142, 'cols': 18, 'header_rows': 4}]; title=Format D5- List of Sanction Order; geo=['State']; warnings=[]
- Format WQ1. PWS Infra and Delivery Point (Water Supply Scheme Source).xls: format=html_table; tables=1; tables_details=[{'rows': 41, 'cols': 25, 'header_rows': 7}]; title=Format WQ1. PWS Infra and Delivery Point (Water Supply Scheme Source); geo=['State', 'District', 'Block']; warnings=[]
- Format WQ2. Remedial Action.xls: format=html_table; tables=1; tables_details=[{'rows': 38, 'cols': 6, 'header_rows': 4}]; title=Format WQ2. Remedial Action; geo=['State', 'District', 'Block']; warnings=[]
- Habitation wise FHTC Coverage( Reported Till 23_08.xls: format=html_table; tables=1; tables_details=[{'rows': 39, 'cols': 22, 'header_rows': 5}]; title=Habitation wise FHTC Coverage( Reported Till 23/08/2026); geo=['State', 'District', 'Habitation']; warnings=[]
- JJM Benchmark - State-wise Implementation in terms.xls: format=html_table; tables=1; tables_details=[{'rows': 38, 'cols': 12, 'header_rows': 4}]; title=JJM Benchmark - State-wise Implementation in terms of FHTCs; geo=['State']; warnings=[]
- JJM Benchmark – Status of Scheme Planning and Cost.xls: format=html_table; tables=1; tables_details=[{'rows': 40, 'cols': 21, 'header_rows': 6}]; title=JJM Benchmark – Status of Scheme Planning and Costs; geo=['State']; warnings=[]
- National Wash Expert Wise Field Visit Report.xls: format=html_table; tables=1; tables_details=[{'rows': 216, 'cols': 13, 'header_rows': 4}]; title=National Wash Expert Wise Field Visit Report; geo=['District', 'Village']; warnings=[]
- Progress at district level.xls: format=html_table; tables=1; tables_details=[{'rows': 757, 'cols': 7, 'header_rows': 3}]; title=Progress at district level; geo=['State', 'District']; warnings=[]
- Progress in Aspirational districts.xls: format=html_table; tables=1; tables_details=[{'rows': 115, 'cols': 7, 'header_rows': 3}]; title=Progress in Aspirational districts; geo=['State', 'District']; warnings=[]
- Progress in JE_AES districts.xls: format=html_table; tables=1; tables_details=[{'rows': 64, 'cols': 7, 'header_rows': 3}]; title=Progress in JE/AES districts; geo=['State', 'District']; warnings=[]
- Progress tracker of verification of schemes (1).xls: format=html_table; tables=1; tables_details=[{'rows': 118, 'cols': 12, 'header_rows': 5}]; title=Progress tracker of verification of schemes; geo=['State', 'Division']; warnings=[]
- Progress tracker of verification of schemes (2).xls: format=html_table; tables=1; tables_details=[{'rows': 43, 'cols': 12, 'header_rows': 4}]; title=Progress tracker of verification of schemes; geo=['State', 'Division']; warnings=[]
- Progress tracker of verification of schemes (3).xls: format=html_table; tables=1; tables_details=[{'rows': 70, 'cols': 12, 'header_rows': 5}]; title=Progress tracker of verification of schemes; geo=['State', 'Division']; warnings=[]
- Progress tracker of verification of schemes.xls: format=html_table; tables=1; tables_details=[{'rows': 16, 'cols': 12, 'header_rows': 5}]; title=Progress tracker of verification of schemes; geo=['State', 'Division']; warnings=[]
- State wise Allocation Release Expenditure.xls: format=html_table; tables=1; tables_details=[{'rows': 38, 'cols': 13, 'header_rows': 4}]; title=State wise Allocation, Release, Expenditure; geo=['State']; warnings=[]
- State wise PWS and FHTC Coverage.xls: format=html_table; tables=1; tables_details=[{'rows': 38, 'cols': 16, 'header_rows': 2}]; title=State wise PWS and FHTC Coverage; geo=['State', 'Village']; warnings=[]
- State wise number of Rural Population as on (01_04.xls: format=html_table; tables=1; tables_details=[{'rows': 38, 'cols': 6, 'header_rows': 2}]; title=State wise number of Rural Population as on (01/04/2026); geo=['State']; warnings=[]
- Status of PWS schemes.xls: format=html_table; tables=1; tables_details=[{'rows': 40, 'cols': 6, 'header_rows': 6}]; title=Status of PWS schemes; geo=['State']; warnings=[]
- Status of Pipe Water Supply in School (1).xls: format=html_table; tables=1; tables_details=[{'rows': 38, 'cols': 14, 'header_rows': 4}]; title=Status of Pipe Water Supply in School; geo=['State', 'District']; warnings=[]
- Status of Pipe Water Supply in School (2).xls: format=text_with_commas; tables=1; tables_details=[{'rows': 19, 'cols': 378}]; title=None; geo=[]; warnings=[]
- Status of Pipe Water Supply in School (3).xls: format=html_table; tables=1; tables_details=[{'rows': 6, 'cols': 14, 'header_rows': 4}]; title=Status of Pipe Water Supply in School; geo=['State', 'District']; warnings=[]
- Status of Pipe Water Supply in School.xls: format=html_table; tables=1; tables_details=[{'rows': 39, 'cols': 14, 'header_rows': 4}]; title=Status of Pipe Water Supply in School; geo=['State', 'District']; warnings=[]
- Status of geo-tagged water sources.xls: format=html_table; tables=1; tables_details=[{'rows': 40, 'cols': 13, 'header_rows': 6}]; title=Status of geo-tagged water sources; geo=['State']; warnings=[]
- Status of user in JJM field user application.xls: format=html_table; tables=1; tables_details=[{'rows': 39, 'cols': 9, 'header_rows': 2}]; title=Status of user in JJM field user application; geo=['State']; warnings=[]
- Status of verification of beneficiary provided wit (1).xls: format=html_table; tables=1; tables_details=[{'rows': 8, 'cols': 8, 'header_rows': 5}]; title=Status of verification of beneficiary provided with tap water supply (30/08/2026); geo=['State', 'District']; warnings=[]
- Status of verification of beneficiary provided wit (2).xls: format=html_table; tables=1; tables_details=[{'rows': 42, 'cols': 8, 'header_rows': 5}]; title=Status of verification of beneficiary provided with tap water supply (30/08/2026); geo=['State', 'District']; warnings=[]
- Status of verification of beneficiary provided wit (3).xls: format=html_table; tables=1; tables_details=[{'rows': 39, 'cols': 8, 'header_rows': 5}]; title=Status of verification of beneficiary provided with tap water supply (30/08/2026); geo=['State', 'District']; warnings=[]
- Status of verification of beneficiary provided wit.xls: format=html_table; tables=1; tables_details=[{'rows': 40, 'cols': 8, 'header_rows': 5}]; title=Status of verification of beneficiary provided with tap water supply (30/08/2026); geo=['State', 'District']; warnings=[]

## E. Version and duplicate analysis
- No exact duplicates by SHA-256 detected

## F. Extraction quality
- AssamDistrict wise number of Rural Population as on (01.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- CS1 A. Coverage.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- CS1 B (ii). Robust chlorination system_ Disinfecti.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- CS1 B(i). Water Quality.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- District wise number of Rural Population as on (01 (1).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- District wise number of Rural Population as on (01 (2).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- District wise number of Rural Population as on (01.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- FHTCDataTable.pdf: extraction_status=text_extracted; quality=good; warnings=[]
- Format - F27 Status of Pipe Water Supply in Ashram.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Format B1- Basic Habitation Information As On 01_0.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Format B15 _ Piped water supply schemes.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Format C17 A- No Of Quality Affected Habitations & (1).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Format C17 A- No Of Quality Affected Habitations & (2).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Format C17 A- No Of Quality Affected Habitations & (3).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Format C17 A- No Of Quality Affected Habitations &.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Format D5- List of Sanction Order.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Format WQ1. PWS Infra and Delivery Point (Water Supply Scheme Source).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Format WQ2. Remedial Action.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Habitation wise FHTC Coverage( Reported Till 23_08.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- JJM Benchmark - State-wise Implementation in terms.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- JJM Benchmark – Status of Scheme Planning and Cost.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- JJM_Operational_Guidelines.pdf: extraction_status=text_extracted; quality=good; warnings=[]
- National Wash Expert Wise Field Visit Report.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Operational-Guidelines-JJM-2.pdf: extraction_status=no_text_extracted; quality=scanned_or_image_pdf; warnings=[]
- Progress at district level.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Progress in Aspirational districts.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Progress in JE_AES districts.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Progress tracker of verification of schemes (1).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Progress tracker of verification of schemes (2).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Progress tracker of verification of schemes (3).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Progress tracker of verification of schemes.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- State wise Allocation Release Expenditure.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- State wise PWS and FHTC Coverage.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- State wise number of Rural Population as on (01_04.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Status of PWS schemes.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Status of Pipe Water Supply in School (1).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Status of Pipe Water Supply in School (2).xls: extraction_status=text_parsed; quality=unknown; warnings=[]
- Status of Pipe Water Supply in School (3).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Status of Pipe Water Supply in School.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Status of geo-tagged water sources.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Status of user in JJM field user application.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Status of verification of beneficiary provided wit (1).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Status of verification of beneficiary provided wit (2).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Status of verification of beneficiary provided wit (3).xls: extraction_status=tables_parsed; quality=unknown; warnings=[]
- Status of verification of beneficiary provided wit.xls: extraction_status=tables_parsed; quality=unknown; warnings=[]

## G. Canonical representation impact
Based on observed corpus, canonical model must preserve: document, page (for PDFs), table sections, rows, columns, header rows, report title, reporting date (where present), and provenance (source file, sha256, mtime). Geographic fields observed: State, District, Division, Village in some reports.

## H. Architecture implications
**Observed from corpus**: many .xls files are HTML table exports; PDFs vary between text and scanned; tables are primary structured artifacts; geographic and format labels appear in text.
**Recommended architecture**: support html-table parsers, robust PDF text extraction with fallback OCR, preserve table structure in canonical form, metadata filtering by format, state, district, date, and exact SHA for duplicate/version handling.
**Still requires validation**: OCR need for scanned PDFs, deeper table structure normalization (merged cells detection), and mapping of format labels to canonical field names.

## I. Validation evidence
- Python: d:\jjm-rag\.venv\Scripts\python.exe 3.11.6 (tags/v3.11.6:8b6ee5b, Oct  2 2023, 14:57:12) [MSC v.1935 64 bit (AMD64)]
- pytest: 9.1.1
- pytest results: 4 passed (from earlier execution in this session)

PHASE 1 STATUS: BLOCKED
Remaining issues: PDFs with no text extracted or failed parsing listed above