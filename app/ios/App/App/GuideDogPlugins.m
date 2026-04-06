@import Capacitor;

CAP_PLUGIN(LiDARPlugin, "LiDARPlugin",
    CAP_PLUGIN_METHOD(isAvailable, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(start, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(stop, CAPPluginReturnPromise);
)

CAP_PLUGIN(AudioPlugin, "AudioPlugin",
    CAP_PLUGIN_METHOD(activate, CAPPluginReturnPromise);
)
