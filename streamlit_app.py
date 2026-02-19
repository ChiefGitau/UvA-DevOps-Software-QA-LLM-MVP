import streamlit as st
import zipfile
import io
from pathlib import Path

st.title("File Reader Application")
st.write("Upload a single file or a zip file to view its contents")

# File uploader
uploaded_file = st.file_uploader(
    "Choose a file",
    type=None,  # Accept all file types
    help="Upload a single file or a zip file"
)

if uploaded_file is not None:
    # Display file information
    st.subheader("File Information")
    file_details = {
        "Filename": uploaded_file.name,
        "File size": f"{uploaded_file.size / 1024:.2f} KB",
        "File type": uploaded_file.type
    }
    st.json(file_details)

    # Check if the file is a zip file
    if uploaded_file.name.endswith('.zip'):
        st.subheader(" Zip File Contents")

        try:
            # Read the zip file
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                # List all files in the zip
                file_list = zip_ref.namelist()
                st.write(f"**Number of files:** {len(file_list)}")

                # Display file list
                st.write("**Files in archive:**")
                for file_name in file_list:
                    st.write(f"- {file_name}")

                # Let user select a file to view
                if file_list:
                    selected_file = st.selectbox(
                        "Select a file to preview",
                        file_list
                    )

                    if st.button("View Selected File"):
                        try:
                            with zip_ref.open(selected_file) as file:
                                content = file.read()

                                # Try to decode as text
                                try:
                                    text_content = content.decode('utf-8')
                                    st.code(text_content, language=None)
                                except UnicodeDecodeError:
                                    st.warning("This file appears to be binary. Showing first 1000 bytes:")
                                    st.text(str(content[:1000]))
                        except Exception as e:
                            st.error(f"Error reading file: {str(e)}")

        except zipfile.BadZipFile:
            st.error("Invalid zip file!")
        except Exception as e:
            st.error(f"Error processing zip file: {str(e)}")

    else:
        # Handle single file
        st.subheader("📄 File Contents")

        try:
            # Try to read as text
            content = uploaded_file.read()

            try:
                text_content = content.decode('utf-8')
                st.code(text_content, language=None)

                # Show line count
                line_count = len(text_content.splitlines())
                st.info(f"Total lines: {line_count}")

            except UnicodeDecodeError:
                st.warning("This file appears to be binary. Showing first 1000 bytes:")
                st.text(str(content[:1000]))

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

        # Reset file pointer for potential re-reading
        uploaded_file.seek(0)

        # Download button
        st.download_button(
            label="Download File",
            data=uploaded_file,
            file_name=uploaded_file.name,
            mime=uploaded_file.type
        )

else:
    st.info("👆 Please upload a file to get started")

    # Display example usage
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        **This application can:**
        - Read and display single text files
        - Extract and browse zip file contents
        - Preview individual files within zip archives
        - Show file metadata (name, size, type)

        **Supported operations:**
        1. Upload any single file to view its contents
        2. Upload a .zip file to see all files inside
        3. Select and preview files from within the zip archive
        """)
