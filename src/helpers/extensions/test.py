try:
    import sz_se_detect

    print("sz_se_detect module is installed")
except ImportError as e:
    print("sz_se_detect module is not installed")
    print(f"Error: {e}")
