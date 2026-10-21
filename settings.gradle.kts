include(":core")

// Load all utility libraries under /lib
val libDir = File(rootDir, "lib")
if (libDir.exists()) {
    libDir.listFiles()?.filter { it.isDirectory }?.forEach { dir ->
        val libName = ":lib-${dir.name}"
        include(libName)
        project(libName).projectDir = dir
    }
}

// Load all multisrc templates under /lib-multisrc
val multisrcDir = File(rootDir, "lib-multisrc")
if (multisrcDir.exists()) {
    multisrcDir.listFiles()?.filter { it.isDirectory }?.forEach { dir ->
        val multiName = ":lib-multisrc-${dir.name}"
        include(multiName)
        project(multiName).projectDir = dir
    }
}

// Automatically discover and load all extensions under /src/{lang}/{name}
val srcDir = File(rootDir, "src")
if (srcDir.exists()) {
    srcDir.listFiles()?.filter { it.isDirectory }?.forEach { langDir ->
        langDir.listFiles()?.filter { it.isDirectory }?.forEach { extDir ->
            val extName = ":extensions:individual:${langDir.name}:${extDir.name}"
            include(extName)
            project(extName).projectDir = extDir
        }
    }
}
