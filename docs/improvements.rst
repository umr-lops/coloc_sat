============
Improvements
============

Python package structure
------------------------

1. Add unitary tests

2. Add an abstract class for the Meta classes (example : GetBaseMeta)

    There are many common attributes between the meta classes. This improvement could
    make a lighter code and make easier the maintenance.

Non-treated cases
-----------------

Some combinations aren't yet treated by this tool. These cases should be treated.
Here is a recap of the treated and non-treated cases:

+-------------------------+-------------------------+-------------------------+-------------------------+-------------------------+
|                         |   truncated_swath       |          swath          |  daily_regular_grid     |           model         |
+=========================+=========================+=========================+=========================+=========================+
| **truncated_swath**     | listing=True,           | listing=True,           | listing=True,           | listing=True,           |
|                         | product_generation=True | product_generation=False| product_generation=True | product_generation=True |
+-------------------------+-------------------------+-------------------------+-------------------------+-------------------------+
| **swath**               | listing=True,           | listing=False,          | listing=False,          | listing=True,           |
|                         | product_generation=False| product_generation=False| product_generation=False| product_generation=False|
+-------------------------+-------------------------+-------------------------+-------------------------+-------------------------+
| **daily_regular_grid**  | listing=True,           | listing=False,          | listing=False,          | listing=True,           |
|                         | product_generation=True | product_generation=False| product_generation=False| product_generation=False|
+-------------------------+-------------------------+-------------------------+-------------------------+-------------------------+
| **model**               | listing=True,           | listing=True,           | listing=True,           | listing=True,           |
|                         | product_generation=True | product_generation=False| product_generation=False| product_generation=False|
+-------------------------+-------------------------+-------------------------+-------------------------+-------------------------+

