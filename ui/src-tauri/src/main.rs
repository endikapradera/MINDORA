#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Child;
use std::sync::Mutex;
use std::sync::Arc;

fn spawn_backend(resource_dir: &std::path::Path) -> Option<Child> {
  // The PyInstaller --onedir bundle is placed in Resources/IA_Core/
  #[cfg(target_os = "windows")]
  let exe_name = "IA_Core.exe";
  #[cfg(not(target_os = "windows"))]
  let exe_name = "IA_Core";

  // Candidate paths for bundled backend.
  // Depending on how Tauri normalizes `../` in `bundle.resources`,
  // resources can land under `_up_/_up_/...`.
  let candidates = [
    resource_dir.join("IA_Core").join(exe_name),
    resource_dir.join("core").join("dist").join("IA_Core").join(exe_name),
    resource_dir
      .join("_up_")
      .join("_up_")
      .join("core")
      .join("dist")
      .join("IA_Core")
      .join(exe_name),
  ];

  let backend_exe = candidates
    .iter()
    .find(|p| p.exists())
    .cloned();

  let Some(backend_exe) = backend_exe else {
    // Dev mode: backend is not bundled, assume it's already running
    eprintln!(
      "[MINDORA] Dev mode: backend exe not found in expected paths under {:?}, assuming already running",
      resource_dir
    );
    return None;
  };

  eprintln!("[MINDORA] Starting backend: {:?}", backend_exe);

  let mut cmd = std::process::Command::new(&backend_exe);
  cmd.env("OMP_NUM_THREADS", "1");
  cmd.env("KMP_DUPLICATE_LIB_OK", "TRUE");
  cmd.env("MKL_SERVICE_FORCE_INTEL", "1");
  cmd.env("IA_OFFLINE_PORT", "8000");
  cmd.stdout(std::process::Stdio::null());
  cmd.stderr(std::process::Stdio::null());

  match cmd.spawn() {
    Ok(child) => {
      eprintln!("[MINDORA] Backend started, pid={}", child.id());
      Some(child)
    }
    Err(e) => {
      eprintln!("[MINDORA] Failed to start backend: {}", e);
      None
    }
  }
}

fn main() {
  // Use Arc<Mutex> so we can share the process handle between setup and event closures
  let backend: Arc<Mutex<Option<Child>>> = Arc::new(Mutex::new(None));
  let backend_for_event = Arc::clone(&backend);

  tauri::Builder::default()
    .setup(move |app| {
      let resource_dir = app
        .path_resolver()
        .resource_dir()
        .expect("Resource dir not found");

      let child = spawn_backend(&resource_dir);
      *backend.lock().unwrap() = child;

      Ok(())
    })
    .on_window_event(move |event| {
      if let tauri::WindowEvent::Destroyed = event.event() {
        if let Some(mut c) = backend_for_event.lock().unwrap().take() {
          eprintln!("[MINDORA] Killing backend pid={}", c.id());
          let _ = c.kill();
          let _ = c.wait();
        }
      }
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
