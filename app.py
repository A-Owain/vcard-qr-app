ValueError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptrunner/exec_code.py", line 85, in exec_func_with_error_handling
    result = func()
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 576, in code_to_exec
    exec(code, module.__dict__)
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
File "/mount/src/vcard-qr-app/app.py", line 253, in <module>
    main()
    ~~~~^^
File "/mount/src/vcard-qr-app/app.py", line 247, in main
    vcard_tab()
    ~~~~~~~~~^^
File "/mount/src/vcard-qr-app/app.py", line 154, in vcard_tab
    qr.make(fit=True)
    ~~~~~~~^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/qrcode/main.py", line 156, in make
    self.best_fit(start=self.version)
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/qrcode/main.py", line 226, in best_fit
    self.version = bisect_left(
    ^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/qrcode/main.py", line 111, in version
    util.check_version(value)
    ~~~~~~~~~~~~~~~~~~^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/qrcode/util.py", line 184, in check_version
    raise ValueError(f"Invalid version (was {version}, expected 1 to 40)")