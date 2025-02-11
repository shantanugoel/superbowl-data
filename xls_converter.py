import json
import pandas as pd
import re
from typing import List, Dict, Any

def clean_column_name(name: str) -> str:
    """
    Convert theme names to Excel-friendly column names.
    Removes special characters and spaces, ensures valid Excel column names.
    """
    # Remove special characters and spaces, replace with underscore
    clean = re.sub(r'[^a-zA-Z0-9]', '_', name)
    # Remove consecutive underscores
    clean = re.sub(r'_+', '_', clean)
    # Remove trailing underscores
    clean = clean.strip('_')
    return clean

def convert_json_to_excel(input_file: str, output_file: str) -> None:
    """
    Convert SuperBowl ads JSON data to Excel format with optimized theme_tags handling for pivot analysis.
    """
    # Read JSON data
    with open(input_file, 'r', encoding='utf-8') as f:
        data: List[Dict[str, Any]] = json.load(f)
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Create the main sheet data
    main_df = df.copy()
    
    # Get all unique themes
    all_themes = set()
    for themes in df['theme_tags']:
        if themes:  # Check if themes is not None
            all_themes.update(themes)
    
    # Sort themes for consistency
    sorted_themes = sorted(all_themes)
    
    # Create binary columns for each theme
    for theme in sorted_themes:
        clean_theme_name = f"Theme_{clean_column_name(theme)}"
        main_df[clean_theme_name] = main_df['theme_tags'].apply(
            lambda x: 1 if theme in (x or []) else 0
        )
    
    # Convert theme_tags array to string for display
    main_df['theme_tags_display'] = main_df['theme_tags'].apply(lambda x: ' | '.join(x) if x else '')
    
    # Organize columns
    theme_columns = [f"Theme_{clean_column_name(theme)}" for theme in sorted_themes]
    base_columns = [
        'year',
        'brand',
        'title',
        'category',
        'theme_tags_display',
        'description',
        'page_url',
        'video_url',
        'original_title'
    ]
    
    # Combine all columns
    all_columns = base_columns + theme_columns
    main_df = main_df[all_columns]
    
    # Create theme summary data
    theme_summary = pd.DataFrame({
        'Theme': sorted_themes,
        'Count': [main_df[f"Theme_{clean_column_name(theme)}"].sum() for theme in sorted_themes]
    })
    theme_summary = theme_summary.sort_values('Count', ascending=False)
    
    # Write to Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Write main data
        main_df.to_excel(writer, index=False, sheet_name='SuperBowl Ads')
        
        # Write theme summary
        theme_summary.to_excel(writer, index=False, sheet_name='Theme Summary')
        
        # Auto-adjust column widths for all sheets
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            df_to_use = main_df if sheet_name == 'SuperBowl Ads' else theme_summary
            
            for idx, col in enumerate(df_to_use.columns):
                max_length = max(
                    df_to_use[col].astype(str).apply(len).max(),
                    len(col)
                )
                adjusted_width = min(max_length + 2, 100)
                worksheet.column_dimensions[chr(65 + idx)].width = adjusted_width

if __name__ == "__main__":
    convert_json_to_excel(
        'enhanced_superbowl_ads.json',
        'superbowl_ads.xlsx'
    )