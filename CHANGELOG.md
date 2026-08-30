# Changelog

## 1.3.0

Version 1.3.0 uses one small implementation for the package tools and saved workspace.

Current core size: **574 lines / 56,083 bytes**. The current expanded-source check is **64,250 bytes**. All three values are smaller than the first public 1.3.0 build.

This repair pass changes these items:

- repeated finite updates now store the one-step map and use the repeated cycle at run time;
- finite-operation checks charge the number of rows that are checked;
- five-input Boolean tables are no longer rejected because of an imaginary search count;
- system matching checks its permutation limit before it starts the search;
- expression rewrite examples and check rows now have separate roles;
- transform records keep the transform details supplied by the caller;
- machine reduction rejects Python key collisions such as `False` and `0`;
- helper proposal parameters that were accepted and ignored were removed;
- experiment selection now uses its claim filter and supplied result value;
- the ambiguous instance method `digest()` and the old internal kernel alias were removed.

The repository has 79 deterministic tests, 500 generated comparison cases, and 16 executable examples.

Programmer and model documentation remain separate.
