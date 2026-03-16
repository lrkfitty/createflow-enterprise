import os

def wrap_mini_series():
    app_path = "app.py"
    
    with open(app_path, 'r') as f:
        lines = f.readlines()
    
    # Locate Start
    start_idx = -1
    for i, line in enumerate(lines):
        if "with tab_series:" in line:
            start_idx = i
            break
            
    if start_idx == -1:
        print("Could not find 'with tab_series:'")
        return

    # Locate End (Start of World Builder)
    end_idx = -1
    for i, line in enumerate(lines):
        if i > start_idx and "with tab_world:" in line:
            end_idx = i
            # Move back to capture comments/whitespace correctly? 
            # Usually comments for next section start a few lines up.
            # detailed check:
            # line 1661: # ==========================================
            # line 1662: # TAB 1.5: WORLD BUILDER
            # line 1663: # ==========================================
            # line 1664: with tab_world:
            # So we should stop at line 1661 (which is index i - 3 if we find it)
            
            # Check for header comments
            if lines[i-1].strip().startswith("# =="):
                 end_idx = i - 3
            else:
                 end_idx = i
            break
            
    if end_idx == -1:
        print("Could not find 'with tab_world:'")
        return

    print(f"Wrapping lines {start_idx} to {end_idx}")

    # Extract Content
    # The content inside `with tab_series:` is currently indented by 4 spaces (mostly).
    # We want to keep `with tab_series:` as is.
    # We want to declare the function inside it.
    # Then put the content inside the function (Indented by ANOTHER 4 spaces).
    
    prefix = lines[:start_idx+1] # Includes 'with tab_series:\n'
    content = lines[start_idx+1:end_idx]
    suffix = lines[end_idx:]
    
    # Create the wrapper
    # We need to make sure we indent the content.
    # Existing content is already indented by 4 spaces (relative to root) because it's under `with tab_series`.
    # We will define the function inside `with tab_series`, so the function def is indented by 4.
    # The content inside the function needs to be indented by 8.
    
    # So we simply add 4 spaces to every line in `content`.
    
    indented_content = []
    for line in content:
        if line.strip(): # If not empty
            indented_content.append("    " + line)
        else:
            indented_content.append(line) # Keep empty lines as is (or empty)

    wrapper_header = [
        "    @st.fragment\n",
        "    def mini_series_ui():\n"
    ]
    
    wrapper_footer = [
        "\n",
        "    mini_series_ui()\n"
    ]
    
    new_lines = prefix + wrapper_header + indented_content + wrapper_footer + suffix
    
    with open(app_path, 'w') as f:
        f.writelines(new_lines)
    
    print("Successfully wrapped Mini Series in fragment.")

if __name__ == "__main__":
    wrap_mini_series()
