// Prevents additional console window on Windows in release, do NOT remove!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    pi_typst_test_desktop_lib::run()
}
