with open("cleaned_watsons_product_links.csv", "r") as file:
    lines = file.read()
    print(len(lines.split("\n")))