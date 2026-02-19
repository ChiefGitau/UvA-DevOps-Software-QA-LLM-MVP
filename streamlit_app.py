import streamlit as st
import zipfile
import time
import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


st.title("File Reader Application")
st.write("Upload a single file or a zip file to view its contents")

# File uploader
uploaded_file = st.file_uploader(
    "Choose a file",
    type=None,  # Accept all file types
    help="Upload a single file or a zip file"
)

def show_sample_analysis():
    st.subheader("Sample Analysis")

    labels = random.sample(["Category A", "Category B", "Category C", "Category D", "Category E"], 4)
    sizes = [random.randint(10, 50) for _ in range(4)]

    col1, col2 = st.columns(2)

    with col1:
        fig1, ax1 = plt.subplots(figsize=(4, 4))
        ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                colors=plt.cm.Pastel1.colors[:4])
        ax1.axis('equal')
        ax1.set_title("Distribution")
        st.pyplot(fig1)
        plt.close(fig1)

    with col2:
        fig2, ax2 = plt.subplots(figsize=(4, 4))
        bar_labels = [f"Group {chr(65+i)}" for i in range(5)]
        bar_values = [random.randint(20, 100) for _ in range(5)]
        bars = ax2.bar(bar_labels, bar_values,
                       color=plt.cm.Pastel2.colors[:5], edgecolor='gray')
        ax2.set_title("Frequency")
        ax2.set_ylabel("Count")
        for bar, val in zip(bars, bar_values):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                     str(val), ha='center', va='bottom', fontsize=9)
        st.pyplot(fig2)
        plt.close(fig2)


if uploaded_file is not None:

    with st.spinner("Processing your file..."):
        progress = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress.progress(i + 1)
        progress.empty()
    st.success("File uploaded successfully!")

    show_sample_analysis()

    st.divider()


    st.subheader("File Information")
    file_details = {
        "Filename": uploaded_file.name,
        "File size": f"{uploaded_file.size / 1024:.2f} KB",
        "File type": uploaded_file.type
    }
    st.json(file_details)


    if uploaded_file.name.endswith('.zip'):
        st.subheader(" Zip File Contents")

        try:

            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                # List all files in the zip
                file_list = zip_ref.namelist()
                st.write(f"**Number of files:** {len(file_list)}")


                st.write("**Files in archive:**")
                for file_name in file_list:
                    st.write(f"- {file_name}")


                if file_list:
                    selected_file = st.selectbox(
                        "Select a file to preview",
                        file_list
                    )

                    if st.button("View Selected File"):
                        try:
                            with zip_ref.open(selected_file) as file:
                                content = file.read()


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

        st.subheader("File Contents")

        try:

            content = uploaded_file.read()

            try:
                text_content = content.decode('utf-8')
                st.code(text_content, language=None)


                line_count = len(text_content.splitlines())
                st.info(f"Total lines: {line_count}")

            except UnicodeDecodeError:
                st.warning("This file appears to be binary. Showing first 1000 bytes:")
                st.text(str(content[:1000]))

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")


        uploaded_file.seek(0)

        # Download button
        st.download_button(
            label="Download File",
            data=uploaded_file,
            file_name=uploaded_file.name,
            mime=uploaded_file.type
        )

else:
    st.info("Please upload a file to get started")

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
