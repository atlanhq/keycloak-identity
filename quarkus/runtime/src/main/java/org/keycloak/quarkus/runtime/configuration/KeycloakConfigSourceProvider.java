/*
 * Copyright 2021 Red Hat, Inc. and/or its affiliates
 * and other contributors as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.keycloak.quarkus.runtime.configuration;


import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

import org.eclipse.microprofile.config.spi.ConfigSource;
import org.eclipse.microprofile.config.spi.ConfigSourceProvider;
import org.jboss.logging.Logger;
import org.keycloak.quarkus.runtime.Environment;

public class KeycloakConfigSourceProvider implements ConfigSourceProvider {

    private static final Logger log = Logger.getLogger(KeycloakConfigSourceProvider.class);

    private static final List<ConfigSource> CONFIG_SOURCES = new ArrayList<>();
    public static PersistedConfigSource PERSISTED_CONFIG_SOURCE;

    // we initialize in a static block to avoid discovering the config sources multiple times when starting the application
    static {
        initializeSources();
    }

    private static void initializeSources() {
        String profile = Environment.getProfile();

        if (profile != null) {
            System.setProperty("quarkus.profile", profile);
        }

        CONFIG_SOURCES.add(new ConfigArgsConfigSource());
        CONFIG_SOURCES.add(new SysPropConfigSource());
        CONFIG_SOURCES.add(new KcEnvConfigSource());
        PERSISTED_CONFIG_SOURCE = new PersistedConfigSource(getPersistedConfigFile());
        CONFIG_SOURCES.add(PERSISTED_CONFIG_SOURCE);

        CONFIG_SOURCES.addAll(new KeycloakPropertiesConfigSource.InFileSystem().getConfigSources(Thread.currentThread().getContextClassLoader()));

        // by enabling this config source we are able to rely on the default settings when running tests
        CONFIG_SOURCES.addAll(new KeycloakPropertiesConfigSource.InClassPath().getConfigSources(Thread.currentThread().getContextClassLoader()));
    }

    /**
     * Mainly for test purposes as MicroProfile Config does not seem to provide a way to reload configsources when the config
     * is released
     */
    public static void reload() {
        CONFIG_SOURCES.clear();
        initializeSources();
    }

    public static Path getPersistedConfigFile() {
        String homeDir = Environment.getHomeDir();

        if (homeDir == null) {
            return Paths.get(System.getProperty("java.io.tmpdir"), PersistedConfigSource.KEYCLOAK_PROPERTIES);
        }

        Path generatedPath = Paths.get(homeDir, "data", "generated");

        generatedPath.toFile().mkdirs();

        return generatedPath.resolve(PersistedConfigSource.KEYCLOAK_PROPERTIES);
    }

    @Override
    public Iterable<ConfigSource> getConfigSources(ClassLoader forClassLoader) {
        return CONFIG_SOURCES;
    }
}
