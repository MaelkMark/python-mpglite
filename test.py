from tabulate import tabulate

print(tabulate([['Alice', 24], ['Bob', 19]], headers=['Name', 'Age'], tablefmt="rounded_grid"))