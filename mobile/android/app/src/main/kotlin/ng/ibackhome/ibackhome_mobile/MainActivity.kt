package ng.ibackhome.ibackhome_mobile

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PrivateKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec

/**
 * ECDSA P-256 key in the Android Keystore. The private key never leaves the device; Dart only
 * gets the public key (base64 X.509 SubjectPublicKeyInfo DER) and signatures (base64 DER).
 * Contract: backend/app/features/evidence/SIGNING.md.
 */
class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "ng.ibackhome/keystore")
            .setMethodCallHandler { call, result ->
                try {
                    val alias = call.argument<String>("alias") ?: throw IllegalArgumentException("alias")
                    when (call.method) {
                        "ensureKey" -> result.success(ensureKey(alias))
                        "sign" -> {
                            val data = call.argument<ByteArray>("data") ?: throw IllegalArgumentException("data")
                            result.success(sign(alias, data))
                        }
                        "deleteKey" -> {
                            KeyStore.getInstance("AndroidKeyStore").apply { load(null) }.deleteEntry(alias)
                            result.success(null)
                        }
                        else -> result.notImplemented()
                    }
                } catch (e: Exception) {
                    result.error("keystore_error", e.message, null)
                }
            }
    }

    private fun store(): KeyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    private fun ensureKey(alias: String): String {
        val ks = store()
        if (!ks.containsAlias(alias)) {
            val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN)
                .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
                .setDigests(KeyProperties.DIGEST_SHA256)
                .build()
            KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore")
                .apply { initialize(spec) }
                .generateKeyPair()
        }
        return Base64.encodeToString(ks.getCertificate(alias).publicKey.encoded, Base64.NO_WRAP)
    }

    private fun sign(alias: String, data: ByteArray): String {
        val key = store().getKey(alias, null) as PrivateKey
        val sig = Signature.getInstance("SHA256withECDSA").apply {
            initSign(key)
            update(data)
        }
        return Base64.encodeToString(sig.sign(), Base64.NO_WRAP)
    }
}
