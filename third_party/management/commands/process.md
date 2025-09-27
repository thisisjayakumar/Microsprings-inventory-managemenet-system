------------VALIDATION OF VENDORS---------
# Show all vendors with detailed brand information
python manage.py validate_vendors --show-brands

# Show only RM vendors
python manage.py validate_vendors --vendor-type rm_vendor

# Show only vendors that have brands
python manage.py validate_vendors --has-brands

# Combination: Show RM vendors with brands, including brand details
python manage.py validate_vendors --vendor-type rm_vendor --has-brands --show-brands


---------IMPORT PROCESS---------------
# 1. First, run a dry-run to see what would happen
python manage.py import_vendors_from_csv vendors.csv --dry-run

# 2. If everything looks good, run the actual import
python manage.py import_vendors vendors.csv --created-by admin

# 3. Validate the imported data
python manage.py validate_vendors

Data would be in folder - management_data