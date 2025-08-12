#!/usr/bin/env python3
"""
Universal News Scraper for Inquirer and Business Mirror
Scrapes both sources, saves Excel files, and uploads to Azure Blob Storage
"""

import os
from datetime import datetime
import importlib
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import both scrapers as modules
def import_scraper(module_name, function_name):
    try:
        module = importlib.import_module(module_name)
        return getattr(module, function_name)
    except Exception as e:
        print(f"❌ Error importing {module_name}: {e}")
        return None

def main():
    # Ensure environment variables are loaded
    load_dotenv()
    
    # Verify Azure connection
    azure_conn = os.getenv('AZURE_CONNECTION_STRING')
    azure_container = os.getenv('AZURE_CONTAINER_NAME')
    if azure_conn and azure_container:
        print("✅ Azure Blob Storage configuration detected")
    else:
        print("⚠️  Azure Blob Storage configuration missing from .env")
    
    # Import enhanced scrapers with dynamic date filtering and improved extraction
    philstar_scraper = import_scraper('scrape_philstar_improved', 'scrape_philstar_news')
    upload_to_azure_philstar = import_scraper('scrape_philstar_improved', 'upload_to_azure_blob')
    
    print("\n📰 Starting Enhanced Universal News Scraping Process...")
    print("🚀 Enhanced Features:")
    print("   • Dynamic date filtering (today & yesterday)")
    print("   • Business Mirror: Enhanced date extraction & category formatting")
    print("   • Inquirer: Improved date filtering accuracy")
    print("   • Philstar: Infinite scroll simulation for more articles")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Import enhanced scraping functions
    inquirer_scraper = import_scraper('scrape_inquirer', 'scrape_inquirer_news')
    businessmirror_scraper = import_scraper('scrape_businessmirror_fixed', 'scrape_businessmirror_news')
    upload_to_azure = import_scraper('scrape_inquirer', 'upload_to_azure_blob')
    upload_to_azure_bm = import_scraper('scrape_businessmirror_fixed', 'upload_to_azure_blob')

    if not inquirer_scraper or not businessmirror_scraper or not upload_to_azure or not upload_to_azure_bm:
        print("❌ Could not import required functions. Exiting.")
        return

    # Scrape Inquirer
    print("\n==============================")
    print("🔍 Scraping Inquirer Business News...")
    inquirer_news = inquirer_scraper()
    if inquirer_news:
        import pandas as pd
        df_inq = pd.DataFrame(inquirer_news)
        inq_filename = "inquirer_news.xlsx"
        df_inq.to_excel(inq_filename, index=False)
        # Add Excel table named 'NewsTable'
        try:
            from openpyxl import load_workbook
            from openpyxl.worksheet.table import Table, TableStyleInfo
            wb = load_workbook(inq_filename)
            ws = wb.active
            nrows = ws.max_row
            ncols = ws.max_column
            col_letters = ws.cell(row=1, column=ncols).column_letter
            table_ref = f"A1:{col_letters}{nrows}"
            table = Table(displayName="NewsTable", ref=table_ref)
            style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                                   showLastColumn=False, showRowStripes=True, showColumnStripes=False)
            table.tableStyleInfo = style
            ws.add_table(table)
            wb.save(inq_filename)
            print(f"📊 Saved {len(df_inq)} Inquirer news items to {inq_filename} (with table 'NewsTable')")
        except Exception as e:
            print(f"⚠️ Could not add Excel table to Inquirer file: {e}")
            print(f"📊 Saved {len(df_inq)} Inquirer news items to {inq_filename}")
        print("☁️ Uploading Inquirer news to Azure...")
        upload_to_azure(inq_filename, inq_filename)
    else:
        print("❌ No Inquirer news found.")

    # Scrape Business Mirror
    print("\n==============================")
    print("🔍 Scraping Business Mirror News...")
    try:
        # Check if file is locked before proceeding
        bm_filename = "businessmirror_news.xlsx"
        if os.path.exists(bm_filename):
            try:
                # Test if we can access the file
                with open(bm_filename, 'r+b') as test_file:
                    pass
            except PermissionError:
                print(f"⚠️  File {bm_filename} is currently locked. Please close any Excel applications and try again.")
                print("   Skipping Business Mirror scraping to continue with other sources...")
                bm_news = None
            except:
                print(f"   Removing existing file: {bm_filename}")
                os.remove(bm_filename)
        
        if 'bm_news' not in locals() or bm_news is None:
            bm_news = businessmirror_scraper()
        
        if bm_news:
            import pandas as pd
            df_bm = pd.DataFrame(bm_news)
            df_bm.to_excel(bm_filename, index=False)
            # Add Excel table named 'NewsTable1'
            try:
                from openpyxl import load_workbook
                from openpyxl.worksheet.table import Table, TableStyleInfo
                wb = load_workbook(bm_filename)
                ws = wb.active
                nrows = ws.max_row
                ncols = ws.max_column
                col_letters = ws.cell(row=1, column=ncols).column_letter
                table_ref = f"A1:{col_letters}{nrows}"
                table = Table(displayName="NewsTable1", ref=table_ref)
                style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                                       showLastColumn=False, showRowStripes=True, showColumnStripes=False)
                table.tableStyleInfo = style
                ws.add_table(table)
                wb.save(bm_filename)
                print(f"📊 Saved {len(df_bm)} Business Mirror news items to {bm_filename} (with table 'NewsTable1')")
            except Exception as e:
                print(f"⚠️ Could not add Excel table to Business Mirror file: {e}")
                print(f"📊 Saved {len(df_bm)} Business Mirror news items to {bm_filename}")
            print("☁️ Uploading Business Mirror news to Azure...")
            upload_to_azure_bm(bm_filename, bm_filename)
        else:
            print("❌ No Business Mirror news found.")
    except Exception as e:
        print(f"❌ Business Mirror scraping failed: {str(e)}")
        if "Permission denied" in str(e):
            print("   💡 Suggestion: Close any Excel files and ensure no applications are using the output file")

    print("\n==============================")
    print("🔍 Scraping Philstar Business News...")
    if philstar_scraper and upload_to_azure_philstar:
        philstar_news = philstar_scraper()
        if philstar_news:
            import pandas as pd
            df_philstar = pd.DataFrame(philstar_news)
            philstar_filename = "philstar_news.xlsx"
            df_philstar.to_excel(philstar_filename, index=False)
            # Add Excel table named 'NewsTable2'
            try:
                from openpyxl import load_workbook
                from openpyxl.worksheet.table import Table, TableStyleInfo
                wb = load_workbook(philstar_filename)
                ws = wb.active
                nrows = ws.max_row
                ncols = ws.max_column
                col_letters = ws.cell(row=1, column=ncols).column_letter
                table_ref = f"A1:{col_letters}{nrows}"
                table = Table(displayName="NewsTable2", ref=table_ref)
                style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                                       showLastColumn=False, showRowStripes=True, showColumnStripes=False)
                table.tableStyleInfo = style
                ws.add_table(table)
                wb.save(philstar_filename)
                print(f"📊 Saved {len(df_philstar)} Philstar news items to {philstar_filename} (with table 'NewsTable2')")
            except Exception as e:
                print(f"⚠️ Could not add Excel table to Philstar file: {e}")
                print(f"📊 Saved {len(df_philstar)} Philstar news items to {philstar_filename}")
            print("☁️ Uploading Philstar news to Azure...")
            upload_to_azure_philstar(philstar_filename, philstar_filename)
        else:
            print("❌ No Philstar news found.")
    else:
        print("❌ Philstar scraper or Azure upload function not available.")

    print("\n==============================")
    print("✅ Enhanced Universal News Scraping Complete!")
    print("🎯 All improvements implemented:")
    print("   ✓ Dynamic date filtering (adapts to any date)")
    print("   ✓ Business Mirror: More articles + proper categories")
    print("   ✓ Inquirer: Better date filtering accuracy")
    print("   ✓ Philstar: Infinite scroll simulation")
    print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
