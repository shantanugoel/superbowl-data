import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any

def convert_json_to_excel(input_file: str, output_file: str) -> None:
    """
    Convert SuperBowl ads JSON data to Excel format with optimized theme_tags handling for pivot analysis.
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output Excel file
    """
    # Read JSON data
    with open(input_file, 'r', encoding='utf-8') as f:
        data: List[Dict[str, Any]] = json.load(f)
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Create the main sheet data
    main_df = df.copy()
    main_df['theme_tags'] = main_df['theme_tags'].apply(lambda x: ' | '.join(x) if x else '')
    
    # Reorder columns for better readability
    main_columns = [
        'year',
        'brand',
        'title',
        'category',
        'theme_tags',
        'description',
        'page_url',
        'video_url',
        'original_title'
    ]
    main_df = main_df[main_columns]
    
    # Create theme analysis data
    # First, get all unique themes
    all_themes = set()
    for themes in df['theme_tags']:
        all_themes.update(themes)
    
    # Create binary columns for each theme
    theme_df = df.copy()
    for theme in sorted(all_themes):
        theme_df[f'Theme_{theme}'] = theme_df['theme_tags'].apply(
            lambda x: 1 if theme in x else 0
        )
    
    # Prepare theme analysis columns
    theme_columns = ['year', 'brand', 'title', 'category'] + [f'Theme_{theme}' for theme in sorted(all_themes)]
    theme_df = theme_df[theme_columns]
    
    # Write to Excel with multiple sheets
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Write main data
        main_df.to_excel(writer, index=False, sheet_name='SuperBowl Ads')
        
        # Write theme analysis data
        theme_df.to_excel(writer, index=False, sheet_name='Theme Analysis')
        
        # Create theme summary
        theme_summary = pd.DataFrame({
            'Theme': sorted(all_themes),
            'Count': [theme_df[f'Theme_{theme}'].sum() for theme in sorted(all_themes)]
        })
        theme_summary = theme_summary.sort_values('Count', ascending=False)
        theme_summary.to_excel(writer, index=False, sheet_name='Theme Summary')
        
        # Auto-adjust column widths for all sheets
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            df_to_use = main_df if sheet_name == 'SuperBowl Ads' else \
                        theme_df if sheet_name == 'Theme Analysis' else \
                        theme_summary
            
            for idx, col in enumerate(df_to_use.columns):
                max_length = max(
                    df_to_use[col].astype(str).apply(len).max(),
                    len(col)
                )
                adjusted_width = min(max_length + 2, 100)
                worksheet.column_dimensions[chr(65 + idx)].width = adjusted_width

        # Create a pivot table
        pivot_sheet = writer.book.create_sheet('Theme Pivot')
        theme_df.to_excel(writer, sheet_name='Theme Pivot', startrow=0, startcol=0, index=False)
        
        # Add a sample pivot table
        pivot_start_row = len(theme_df) + 3
        pivot_sheet.cell(row=pivot_start_row, column=1, value="Sample Pivot Table Below:")
        
if __name__ == "__main__":
    convert_json_to_excel(
        'enhanced_superbowl_ads.json',
        'superbowl_ads.xlsx'
    )