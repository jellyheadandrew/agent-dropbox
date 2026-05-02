use notify::{Config, Event, RecommendedWatcher, RecursiveMode, Watcher};
use std::path::PathBuf;
use std::sync::mpsc;
use std::time::Duration;

pub struct FolderWatcher {
    _watcher: RecommendedWatcher,
}

impl FolderWatcher {
    pub fn new(
        path: PathBuf,
        debounce_secs: u64,
        on_change: impl Fn() + Send + 'static,
    ) -> Result<Self, String> {
        let (tx, rx) = mpsc::channel();

        let mut watcher = RecommendedWatcher::new(
            move |result: Result<Event, notify::Error>| {
                if result.is_ok() {
                    let _ = tx.send(());
                }
            },
            Config::default(),
        )
        .map_err(|e| format!("Watcher init error: {}", e))?;

        watcher
            .watch(&path, RecursiveMode::Recursive)
            .map_err(|e| format!("Watch error: {}", e))?;

        let debounce = Duration::from_secs(debounce_secs);
        std::thread::spawn(move || {
            loop {
                match rx.recv() {
                    Ok(()) => {
                        // Drain all pending events within debounce window
                        while rx.recv_timeout(debounce).is_ok() {}
                        on_change();
                    }
                    Err(_) => break,
                }
            }
        });

        Ok(Self { _watcher: watcher })
    }
}
