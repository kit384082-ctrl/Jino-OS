🧪 [testing improvement] Add bounds check to window_create in api_server.py

🎯 **What:** The `window_create` function blindly inserted new windows into a static array sized 16, resulting in a buffer overflow if 17 windows are created. The fix adds a missing error path bounds check that halts the creation if the internal counter reaches 16. A new unit test script verifies this missing coverage.

📊 **Coverage:** A new suite of unit tests has been developed in `tests/test_api_server.c`, testing the state of `window_create` window creation. The 16 window insertion scenarios have been covered and the bounds check to ensure it returns `-1` (missing error path) is now covered.

✨ **Result:** 100% test coverage against a missing error path limit, significantly preventing dangerous buffer overflows in the code base array bound limit.
