#!/bin/bash
# RCSB PDB ChatBot - User Data Management Script
# Standalone script for managing user session data

set -e

echo "📂 RCSB PDB ChatBot - Data Management"
echo "===================================="

# Check if we're in the right directory
if [[ ! -f "docker-compose.yml" ]]; then
    echo "❌ Error: docker-compose.yml not found. Please run this script from the project directory."
    exit 1
fi

# Display current data status
show_data_status() {
    echo ""
    echo "📊 Current Data Status"
    echo "===================="

    if [[ -d "user_data" ]] && [[ -n "$(ls -A user_data 2>/dev/null)" ]]; then
        echo "📁 Directory: $(pwd)/user_data"

        local session_count=$(ls -1 user_data/*.json 2>/dev/null | wc -l)
        echo "📝 Session files: $session_count"

        echo ""
        echo "👥 User Sessions:"
        for file in user_data/user_*_sessions.json; do
            if [[ -f "$file" ]]; then
                local user_id=$(basename "$file" | sed 's/user_\(.*\)_sessions\.json/\1/')
                local chat_count=$(jq -r '.chats | length' "$file" 2>/dev/null || echo "0")
                local file_size=$(du -h "$file" | cut -f1)
                echo "   - User: $user_id | Chats: $chat_count | Size: $file_size"
            fi
        done 2>/dev/null

        local total_size=$(du -sh user_data 2>/dev/null | cut -f1 || echo "0B")
        echo ""
        echo "💾 Total size: $total_size"
    else
        echo "📂 No user data found"
    fi
}

# Backup function
backup_data() {
    local timestamp=$(date +"%Y-%m-%d_%H%M%S")
    local backup_dir="backups/user_data_${timestamp}"

    echo ""
    echo "💾 Creating Backup"
    echo "=================="

    mkdir -p "${backup_dir}"

    if [[ -d "user_data" ]] && [[ -n "$(ls -A user_data 2>/dev/null)" ]]; then
        cp -r user_data/* "${backup_dir}/" 2>/dev/null || true

        # Create backup metadata
        echo "# Backup Metadata" > "${backup_dir}/backup_info.md"
        echo "Backup Date: $(date)" >> "${backup_dir}/backup_info.md"
        echo "Source Directory: $(pwd)/user_data" >> "${backup_dir}/backup_info.md"
        echo "Files Backed Up:" >> "${backup_dir}/backup_info.md"
        ls -la "${backup_dir}"/*.json 2>/dev/null | awk '{print "- " $9 " (" $5 " bytes)"}' >> "${backup_dir}/backup_info.md" || true

        echo "✅ Backup created: ${backup_dir}"
        echo "   Files backed up: $(ls -1 "${backup_dir}"/*.json 2>/dev/null | wc -l)"

        # Show backup size
        local backup_size=$(du -sh "${backup_dir}" 2>/dev/null | cut -f1 || echo "0B")
        echo "   Backup size: $backup_size"
    else
        echo "⚠️  No data to backup"
        rmdir "${backup_dir}" 2>/dev/null || true
    fi
}

# Restore function
restore_data() {
    echo ""
    echo "🔄 Restore Data"
    echo "==============="

    if [[ ! -d "backups" ]] || [[ -z "$(ls -A backups 2>/dev/null)" ]]; then
        echo "❌ No backups found in 'backups/' directory"
        return 1
    fi

    echo "📦 Available backups:"
    local i=1
    declare -a backup_dirs
    for backup_dir in backups/user_data_*; do
        if [[ -d "$backup_dir" ]]; then
            backup_dirs[$i]="$backup_dir"
            local backup_date=$(basename "$backup_dir" | sed 's/user_data_//' | sed 's/_/ /')
            local file_count=$(ls -1 "$backup_dir"/*.json 2>/dev/null | wc -l || echo "0")
            local size=$(du -sh "$backup_dir" 2>/dev/null | cut -f1 || echo "0B")
            echo "   $i) $backup_date ($file_count files, $size)"
            ((i++))
        fi
    done

    if [[ ${#backup_dirs[@]} -eq 0 ]]; then
        echo "❌ No valid backups found"
        return 1
    fi

    echo ""
    read -p "Choose backup to restore (1-$((i-1)), 0 to cancel): " choice

    if [[ "$choice" =~ ^[1-9][0-9]*$ ]] && [[ "$choice" -le ${#backup_dirs[@]} ]]; then
        local selected_backup="${backup_dirs[$choice]}"

        echo ""
        echo "⚠️  This will replace all current user data!"
        read -p "Continue with restore? (y/N): " confirm

        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            # Backup current data before restore
            if [[ -d "user_data" ]] && [[ -n "$(ls -A user_data 2>/dev/null)" ]]; then
                echo "💾 Backing up current data before restore..."
                backup_data
            fi

            # Clear current data
            rm -rf user_data/*
            mkdir -p user_data

            # Restore from backup
            cp -r "${selected_backup}"/*.json user_data/ 2>/dev/null || true
            echo "✅ Data restored from: $selected_backup"

            # Show restored data status
            show_data_status
        else
            echo "❌ Restore cancelled"
        fi
    else
        echo "❌ Restore cancelled"
    fi
}

# Export specific user data
export_user() {
    echo ""
    echo "📤 Export User Data"
    echo "=================="

    if [[ ! -d "user_data" ]] || [[ -z "$(ls -A user_data 2>/dev/null)" ]]; then
        echo "❌ No user data found to export"
        return 1
    fi

    echo "👥 Available users:"
    local i=1
    declare -a user_files
    for file in user_data/user_*_sessions.json; do
        if [[ -f "$file" ]]; then
            user_files[$i]="$file"
            local user_id=$(basename "$file" | sed 's/user_\(.*\)_sessions\.json/\1/')
            local chat_count=$(jq -r '.chats | length' "$file" 2>/dev/null || echo "0")
            local size=$(du -h "$file" | cut -f1)
            echo "   $i) $user_id ($chat_count chats, $size)"
            ((i++))
        fi
    done

    if [[ ${#user_files[@]} -eq 0 ]]; then
        echo "❌ No user session files found"
        return 1
    fi

    echo ""
    read -p "Choose user to export (1-$((i-1)), 0 to cancel): " choice

    if [[ "$choice" =~ ^[1-9][0-9]*$ ]] && [[ "$choice" -le ${#user_files[@]} ]]; then
        local selected_file="${user_files[$choice]}"
        local user_id=$(basename "$selected_file" | sed 's/user_\(.*\)_sessions\.json/\1/')
        local timestamp=$(date +"%Y-%m-%d_%H%M%S")
        local export_dir="exports/user_${user_id}_${timestamp}"

        mkdir -p "${export_dir}"
        cp "$selected_file" "${export_dir}/"

        # Create export summary
        echo "# User Export Summary" > "${export_dir}/export_summary.md"
        echo "Export Date: $(date)" >> "${export_dir}/export_summary.md"
        echo "User ID: $user_id" >> "${export_dir}/export_summary.md"
        echo "Source File: $selected_file" >> "${export_dir}/export_summary.md"

        local chat_count=$(jq -r '.chats | length' "$selected_file" 2>/dev/null || echo "0")
        echo "Total Chats: $chat_count" >> "${export_dir}/export_summary.md"

        echo "✅ User data exported to: $export_dir"
    else
        echo "❌ Export cancelled"
    fi
}

# Clear all data
clear_all_data() {
    echo ""
    echo "🗑️  Clear All Data"
    echo "=================="

    if [[ ! -d "user_data" ]] || [[ -z "$(ls -A user_data 2>/dev/null)" ]]; then
        echo "📂 No user data to clear"
        return 0
    fi

    show_data_status

    echo ""
    echo "⚠️  WARNING: This will permanently delete ALL user data!"
    echo "💡 Consider creating a backup first (option 2 in main menu)"
    echo ""
    read -p "Type 'DELETE' to confirm data deletion: " confirm

    if [[ "$confirm" == "DELETE" ]]; then
        echo "💾 Creating safety backup before deletion..."
        backup_data

        rm -rf user_data/*
        mkdir -p user_data
        echo "✅ All user data cleared"
        echo "📁 Empty user_data directory ready"
    else
        echo "❌ Clear operation cancelled"
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "🛠️  Data Management Options"
    echo "=========================="
    echo "1) Show data status"
    echo "2) Backup all data"
    echo "3) Restore from backup"
    echo "4) Export specific user"
    echo "5) Clear all data"
    echo "6) Exit"
    echo ""
    read -p "Choose option (1-6): " choice

    case "$choice" in
        1) show_data_status ;;
        2) backup_data ;;
        3) restore_data ;;
        4) export_user ;;
        5) clear_all_data ;;
        6) echo "👋 Goodbye!"; exit 0 ;;
        *) echo "❌ Invalid option" ;;
    esac
}

# Initial status display
show_data_status

# Main loop
while true; do
    show_menu
done