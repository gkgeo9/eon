#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Settings Page - Manage custom prompts and preferences.
"""

import streamlit as st
from fintel.ui.database import DatabaseRepository
from fintel.ui.utils.validators import validate_prompt_template, validate_prompt_name
from fintel.ui.theme import apply_theme

# Apply global theme
apply_theme()


# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

if 'show_prompt_editor' not in st.session_state:
    st.session_state.show_prompt_editor = False

if 'edit_prompt_id' not in st.session_state:
    st.session_state.edit_prompt_id = None

db = st.session_state.db

st.title("⚙️ Settings")
st.markdown("Manage custom prompts and preferences")

st.markdown("---")

# Tabs for different settings
tab1, tab2, tab3 = st.tabs(["📝 Custom Prompts", "🗂️ File Cache", "🎨 Theme"])

with tab1:
    st.subheader("Custom Prompt Library")
    st.markdown("Create and manage custom prompts for different analysis types.")

    # Analysis type selector
    analysis_type = st.selectbox(
        "Analysis Type",
        options=["fundamental", "buffett", "taleb", "contrarian"],
        help="Select analysis type to view/create prompts"
    )

    # Get prompts for selected type
    prompts = db.get_prompts_by_type(analysis_type)

    st.markdown("---")

    # Display existing prompts
    if prompts:
        st.markdown(f"**Saved Prompts ({len(prompts)})**")

        for prompt in prompts:
            with st.expander(f"📄 {prompt['name']}"):
                st.caption(f"Created: {prompt['created_at']}")

                if prompt.get('description'):
                    st.markdown(f"**Description:** {prompt['description']}")

                st.text_area(
                    "Prompt Template",
                    value=prompt['template'],
                    height=200,
                    disabled=True,
                    key=f"view_{prompt['id']}"
                )

                col1, col2 = st.columns(2)

                with col1:
                    if st.button(f"✏️ Edit", key=f"edit_{prompt['id']}"):
                        st.session_state.edit_prompt_id = prompt['id']
                        st.session_state.show_prompt_editor = True
                        st.rerun()

                with col2:
                    if st.button(f"🗑️ Delete", key=f"delete_{prompt['id']}", type="secondary"):
                        try:
                            db.delete_prompt(prompt['id'])
                            st.success(f"Deleted prompt: {prompt['name']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting prompt: {e}")
    else:
        st.info(f"No custom prompts for {analysis_type} analysis. Create one below!")

    st.markdown("---")

    # Create new prompt button
    if st.button("➕ Create New Prompt", type="primary"):
        st.session_state.show_prompt_editor = True
        st.session_state.edit_prompt_id = None
        st.rerun()

    # Prompt editor (modal-style using expander)
    if st.session_state.show_prompt_editor:
        st.markdown("---")

        # Check if editing existing prompt
        edit_mode = st.session_state.edit_prompt_id is not None

        if edit_mode:
            # Safely find the prompt - handle case where it may have been deleted
            matching_prompts = [p for p in prompts if p['id'] == st.session_state.edit_prompt_id]
            if not matching_prompts:
                st.error("Prompt not found. It may have been deleted.")
                st.session_state.show_prompt_editor = False
                st.session_state.edit_prompt_id = None
                st.rerun()

            existing_prompt = db.get_prompt_by_name(matching_prompts[0]['name'])
            if not existing_prompt:
                st.error("Failed to load prompt details.")
                st.session_state.show_prompt_editor = False
                st.session_state.edit_prompt_id = None
                st.rerun()

            st.subheader(f"✏️ Edit Prompt: {existing_prompt['name']}")
        else:
            st.subheader("➕ Create New Prompt")

        with st.form("prompt_form"):
            name = st.text_input(
                "Prompt Name",
                value=existing_prompt['name'] if edit_mode else "",
                placeholder="e.g., Deep Value Analysis",
                help="Unique name for this prompt"
            )

            description = st.text_area(
                "Description (Optional)",
                value=existing_prompt.get('description', '') if edit_mode else "",
                placeholder="Brief description of what this prompt does",
                height=80
            )

            template = st.text_area(
                "Prompt Template",
                value=existing_prompt.get('prompt_template', existing_prompt.get('template', '')) if edit_mode else "",
                placeholder="Enter your prompt template here. Use {ticker} and {year} as placeholders.",
                height=300,
                help="Use {ticker} and {year} as placeholders that will be replaced during analysis"
            )

            st.caption("💡 **Tip:** Include {ticker} and {year} placeholders in your prompt")

            col1, col2 = st.columns(2)

            with col1:
                submitted = st.form_submit_button(
                    "💾 Save" if edit_mode else "➕ Create",
                    type="primary",
                    width="stretch"
                )

            with col2:
                cancelled = st.form_submit_button(
                    "❌ Cancel",
                    width="stretch"
                )

            if cancelled:
                st.session_state.show_prompt_editor = False
                st.session_state.edit_prompt_id = None
                st.rerun()

            if submitted:
                # Validate
                name_valid, name_error = validate_prompt_name(name)
                template_valid, template_error = validate_prompt_template(template)

                if not name_valid:
                    st.error(f"Invalid name: {name_error}")
                elif not template_valid:
                    st.error(f"Invalid template: {template_error}")
                else:
                    try:
                        if edit_mode:
                            # Update existing
                            db.update_prompt(
                                st.session_state.edit_prompt_id,
                                name=name,
                                description=description,
                                prompt_template=template
                            )
                            st.success(f"✅ Updated prompt: {name}")
                        else:
                            # Create new
                            db.save_prompt(
                                name=name,
                                description=description,
                                prompt_template=template,
                                analysis_type=analysis_type
                            )
                            st.success(f"✅ Created prompt: {name}")

                        st.session_state.show_prompt_editor = False
                        st.session_state.edit_prompt_id = None
                        st.rerun()

                    except Exception as e:
                        if "UNIQUE constraint failed" in str(e):
                            st.error(f"❌ A prompt with name '{name}' already exists")
                        else:
                            st.error(f"❌ Error saving prompt: {e}")

with tab2:
    st.subheader("File Cache Management")
    st.markdown("Manage cached SEC filings to free up disk space.")

    # Get cache statistics
    cache_count = db.get_cache_count()

    st.metric("Cached Files", cache_count)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Clear All Cache", type="secondary", width="stretch"):
            if st.session_state.get('confirm_clear_cache', False):
                deleted = db.clear_file_cache()
                st.success(f"✅ Cleared {deleted} cached files")
                st.session_state.confirm_clear_cache = False
                st.rerun()
            else:
                st.session_state.confirm_clear_cache = True
                st.warning("⚠️ Click again to confirm")

    with col2:
        if st.button("🧹 Clear Old Cache (30+ days)", width="stretch"):
            deleted = db.clear_file_cache(older_than_days=30)
            st.success(f"✅ Cleared {deleted} old cached files")
            st.rerun()

with tab3:
    st.subheader("🎨 Theme Settings")
    st.markdown("Customize the appearance of Fintel")

    # Get current theme preference from user settings
    current_theme = db.get_setting("theme", default="light")

    # Dark mode toggle
    dark_mode = st.toggle(
        "🌙 Dark Mode",
        value=(current_theme == "dark"),
        help="Toggle between light and dark themes"
    )

    # Save preference
    new_theme = "dark" if dark_mode else "light"
    if new_theme != current_theme:
        db.save_setting("theme", new_theme)
        st.rerun()

    # Theme status message (CSS applied via theme.py)
    if dark_mode:
        st.success("🌙 **Dark Mode Active**")
    else:
        st.info("☀️ **Light Mode Active**")

    st.markdown("---")
    st.caption("💡 Theme preference is saved automatically")

# Navigation
st.markdown("---")
if st.button("🏠 Back to Home"):
    st.switch_page("streamlit_app.py")
