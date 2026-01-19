# Mastery-Level Gradle Learning Plan for Spring Boot Developers

A structured 12-16 week curriculum for achieving deep proficiency in Gradle, emphasizing modern Kotlin DSL, convention plugins, multi-project architecture, and Spring Boot optimization. This plan builds from fundamentals through advanced plugin development, following your preference for depth-first learning.

---

## Learning Philosophy

Gradle's complexity stems from its layered architecture: Groovy/Kotlin DSL → Gradle API → Plugin ecosystem → Build lifecycle. Unlike tools with simpler mental models, Gradle rewards deep understanding of its internals. This plan prioritizes understanding **why** Gradle works the way it does, not just **how** to configure it.

**Key insight**: Most Gradle frustration comes from treating it as a configuration file format rather than an executable program. Build scripts are code that runs during the configuration phase, producing a task graph that executes during the execution phase.

---

## Phase 1: Gradle Fundamentals and Mental Model (Weeks 1-3)

**Goal**: Build accurate mental models of Gradle's execution phases, task graph, and core APIs.

### Week 1: Architecture and Lifecycle

**Core concepts to master**:
- **Three-phase execution model**: Initialization → Configuration → Execution
- **Project hierarchy**: Settings, root project, subprojects
- **Task graph construction**: How dependencies create the directed acyclic graph (DAG)
- **Gradle vs Groovy/Kotlin**: The build script is code, not configuration

**The critical insight**: During configuration, ALL build scripts execute for ALL projects, regardless of which task you're running. This is why configuration-time logic must be efficient.

```kotlin
// This runs during CONFIGURATION (every build)
println("Configuring ${project.name}")

tasks.register("myTask") {
    // This block runs during CONFIGURATION
    println("Configuring myTask")
    
    doLast {
        // This runs during EXECUTION (only if task runs)
        println("Executing myTask")
    }
}
```

**Resources**:
| Type | Resource | Notes |
|------|----------|-------|
| Official docs | [Gradle Build Lifecycle](https://docs.gradle.org/current/userguide/build_lifecycle.html) | Essential reading |
| Official docs | [Authoring Tasks](https://docs.gradle.org/current/userguide/more_about_tasks.html) | Task fundamentals |
| Video | Tom Gregory's [Gradle Tutorial](https://www.youtube.com/playlist?list=PL7NT0XqMQBqrX-8daqI7WM0FT3AnfaI4e) | Excellent visual explanations |

**Hands-on exercises**:
1. Add println statements at different points in a build script to observe configuration vs execution timing
2. Create tasks with dependencies and run with `--dry-run` to see the task graph
3. Use `./gradlew tasks --all` to explore available tasks

### Week 2: Kotlin DSL Fundamentals

**Why Kotlin DSL**: Type-safe accessors, IDE auto-completion, compile-time error detection, and better refactoring support. As of Gradle 9, Kotlin DSL is the default and recommended approach.

**Key patterns to learn**:

```kotlin
// Property assignment vs method call
java {
    sourceCompatibility = JavaVersion.VERSION_21  // Property
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))  // Lazy property
    }
}

// Configuring existing tasks vs creating new ones
tasks.named<Test>("test") {
    useJUnitPlatform()
}

tasks.register<Copy>("copyDocs") {
    from("docs")
    into(layout.buildDirectory.dir("docs"))
}

// Container access patterns
val test by tasks.getting(Test::class)  // Delegate
val myTask = tasks.named("myTask")      // Provider
```

**Resources**:
- [Kotlin DSL Primer](https://docs.gradle.org/current/userguide/kotlin_dsl.html) - Official guide
- [Migrating from Groovy to Kotlin DSL](https://docs.gradle.org/current/userguide/migrating_from_groovy_to_kotlin_dsl.html)

**Migration exercise**: Convert a Groovy-based Spring Boot build.gradle to Kotlin DSL manually (don't use automated conversion tools initially—you learn more by doing it yourself).

### Week 3: Dependency Management Deep Dive

**Concepts to master**:
- **Configurations**: api, implementation, compileOnly, runtimeOnly, testImplementation
- **Dependency resolution**: How Gradle resolves version conflicts
- **BOMs and platforms**: Aligning versions across dependencies
- **Transitive dependencies**: Understanding the dependency tree

**Spring Boot dependency management pattern**:

```kotlin
plugins {
    id("org.springframework.boot") version "3.3.0"
    id("io.spring.dependency-management") version "1.1.4"
}

dependencies {
    // BOM manages versions - no version needed
    implementation("org.springframework.boot:spring-boot-starter-web")
    
    // Override BOM version when needed
    implementation("com.fasterxml.jackson.core:jackson-databind") {
        version {
            strictly("2.15.3")  // Force specific version
        }
    }
    
    // Constraints for transitive dependencies
    constraints {
        implementation("org.apache.logging.log4j:log4j-core") {
            version {
                require("2.21.0")
            }
            because("CVE-2021-44228 mitigation")
        }
    }
}
```

**Hands-on**:
1. Run `./gradlew dependencies` to explore the dependency tree
2. Create a scenario with version conflicts and observe resolution
3. Experiment with dependency constraints and strict versions

### Phase 1 Milestone Project

Build a simple multi-module project with:
- Root project with shared configuration
- `app` module (Spring Boot application)
- `core` module (library)
- Proper dependency relationships

---

## Phase 2: Version Catalogs and Centralized Dependencies (Weeks 4-5)

**Goal**: Master modern dependency management with libs.versions.toml.

### Week 4: Version Catalog Fundamentals

Version catalogs provide centralized, type-safe dependency management. The default location is `gradle/libs.versions.toml`.

**Complete catalog structure**:

```toml
[versions]
kotlin = "2.0.0"
spring-boot = "3.3.0"
spring-dependency-management = "1.1.4"
jackson = "2.17.1"

[libraries]
# Full format
spring-boot-starter-web = { module = "org.springframework.boot:spring-boot-starter-web" }
spring-boot-starter-test = { module = "org.springframework.boot:spring-boot-starter-test" }

# With version reference
jackson-databind = { module = "com.fasterxml.jackson.core:jackson-databind", version.ref = "jackson" }
jackson-kotlin = { module = "com.fasterxml.jackson.module:jackson-module-kotlin", version.ref = "jackson" }

# For use in buildSrc/convention plugins
spring-boot-gradle-plugin = { module = "org.springframework.boot:spring-boot-gradle-plugin", version.ref = "spring-boot" }

[bundles]
jackson = ["jackson-databind", "jackson-kotlin"]

[plugins]
kotlin-jvm = { id = "org.jetbrains.kotlin.jvm", version.ref = "kotlin" }
kotlin-spring = { id = "org.jetbrains.kotlin.plugin.spring", version.ref = "kotlin" }
spring-boot = { id = "org.springframework.boot", version.ref = "spring-boot" }
spring-dependency-management = { id = "io.spring.dependency-management", version.ref = "spring-dependency-management" }
```

**Usage in build scripts**:

```kotlin
plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.spring.boot)
}

dependencies {
    implementation(libs.spring.boot.starter.web)
    implementation(libs.bundles.jackson)
    testImplementation(libs.spring.boot.starter.test)
}
```

**Naming conventions** (from Gradle blog):
- Use dashes to separate segments: `spring-boot-starter-web`
- Suffix plugin libraries with `-plugin`: `spring-boot-gradle-plugin`
- Don't repeat redundant parts: `jackson-databind` not `jackson-core-databind`

### Week 5: Sharing Catalogs with Build Logic

**Critical pattern**: Making version catalogs available in buildSrc or build-logic.

```kotlin
// buildSrc/settings.gradle.kts OR build-logic/settings.gradle.kts
dependencyResolutionManagement {
    versionCatalogs {
        create("libs") {
            from(files("../gradle/libs.versions.toml"))
        }
    }
}
```

```kotlin
// buildSrc/build.gradle.kts
plugins {
    `kotlin-dsl`
}

repositories {
    mavenCentral()
    gradlePluginPortal()
}

dependencies {
    // Reference plugins as libraries for use in convention plugins
    implementation(libs.spring.boot.gradle.plugin)
}
```

**Hands-on project**: Migrate an existing Spring Boot project to use version catalogs, including proper buildSrc integration.

---

## Phase 3: Convention Plugins for Multi-Project Builds (Weeks 6-9)

**Goal**: Master convention plugins using both buildSrc and included builds.

### Week 6: Convention Plugin Fundamentals

**What convention plugins solve**:
- Eliminate duplication across subproject build scripts
- Enforce organizational standards
- Create project "types" (library, application, service)
- Encapsulate complex configuration

**Precompiled script plugins** are the simplest approach. A file named `my-convention.gradle.kts` in `buildSrc/src/main/kotlin/` becomes a plugin with ID `my-convention`.

**Layered convention plugin pattern**:

```
buildSrc/src/main/kotlin/
├── kotlin-common-conventions.gradle.kts     # Base Kotlin config
├── spring-boot-conventions.gradle.kts       # Spring Boot apps (applies kotlin-common)
├── spring-library-conventions.gradle.kts    # Spring libraries (applies kotlin-common)
└── integration-test-conventions.gradle.kts  # Adds integration tests
```

### Week 7: Building Convention Plugins

**kotlin-common-conventions.gradle.kts**:

```kotlin
plugins {
    id("org.jetbrains.kotlin.jvm")
}

repositories {
    mavenCentral()
}

kotlin {
    jvmToolchain(21)
    
    compilerOptions {
        freeCompilerArgs.add("-Xjsr305=strict")
    }
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
}
```

**spring-boot-conventions.gradle.kts**:

```kotlin
plugins {
    id("kotlin-common-conventions")  // Apply our base
    id("org.springframework.boot")
    id("io.spring.dependency-management")
    id("org.jetbrains.kotlin.plugin.spring")
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}

tasks.named<org.springframework.boot.gradle.tasks.bundling.BootJar>("bootJar") {
    archiveFileName.set("${project.name}.jar")
}
```

**spring-library-conventions.gradle.kts**:

```kotlin
plugins {
    id("kotlin-common-conventions")
    id("java-library")
    id("io.spring.dependency-management")
    id("org.jetbrains.kotlin.plugin.spring")
}

// Apply Spring Boot BOM without the plugin
dependencyManagement {
    imports {
        mavenBom(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES)
    }
}
```

**Subproject usage**:

```kotlin
// api-service/build.gradle.kts
plugins {
    id("spring-boot-conventions")
}

dependencies {
    implementation(project(":core"))
    implementation("org.springframework.boot:spring-boot-starter-web")
}
```

```kotlin
// core/build.gradle.kts
plugins {
    id("spring-library-conventions")
}

dependencies {
    api("org.springframework.boot:spring-boot-starter-validation")
}
```

### Week 8: buildSrc vs Included Builds (build-logic)

**Current Gradle recommendation**: Use included builds (build-logic) over buildSrc.

**Why**:
1. **Build cache behavior**: Changes to buildSrc invalidate the entire build. Included builds have more granular invalidation.
2. **Dependency resolution**: buildSrc has subtle differences in how dependencies are resolved.
3. **Mental model**: Included builds are treated like external dependencies—simpler to understand.

**build-logic setup**:

```
project-root/
├── build-logic/
│   ├── settings.gradle.kts
│   ├── build.gradle.kts
│   └── src/main/kotlin/
│       └── conventions/
│           ├── kotlin-common-conventions.gradle.kts
│           └── spring-boot-conventions.gradle.kts
├── app/
├── core/
├── settings.gradle.kts
└── gradle/
    └── libs.versions.toml
```

**build-logic/settings.gradle.kts**:

```kotlin
dependencyResolutionManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
    
    versionCatalogs {
        create("libs") {
            from(files("../gradle/libs.versions.toml"))
        }
    }
}

rootProject.name = "build-logic"
```

**build-logic/build.gradle.kts**:

```kotlin
plugins {
    `kotlin-dsl`
}

dependencies {
    implementation(libs.spring.boot.gradle.plugin)
    implementation(libs.kotlin.gradle.plugin)
}
```

**Root settings.gradle.kts**:

```kotlin
pluginManagement {
    includeBuild("build-logic")
}

rootProject.name = "my-project"

include("app", "core")
```

### Week 9: Advanced Convention Plugin Patterns

**Adding test suites with JVM Test Suite plugin**:

```kotlin
// integration-test-conventions.gradle.kts
plugins {
    id("jvm-test-suite")
}

testing {
    suites {
        val integrationTest by registering(JvmTestSuite::class) {
            dependencies {
                implementation(project())
            }
            
            targets {
                all {
                    testTask.configure {
                        shouldRunAfter(tasks.named("test"))
                    }
                }
            }
        }
    }
}

tasks.named("check") {
    dependsOn(testing.suites.named("integrationTest"))
}
```

**Extension for configuration**:

```kotlin
// In build-logic/src/main/kotlin/conventions/MyExtension.kt
abstract class ServiceExtension {
    abstract val serviceName: Property<String>
    abstract val enableMetrics: Property<Boolean>
    
    init {
        enableMetrics.convention(true)
    }
}

// In service-conventions.gradle.kts
val extension = extensions.create<ServiceExtension>("service")

afterEvaluate {
    if (extension.enableMetrics.get()) {
        dependencies {
            add("implementation", "io.micrometer:micrometer-registry-prometheus")
        }
    }
}
```

### Phase 3 Milestone Project

Create a complete multi-module Spring Boot project with:
- Included build (build-logic) with convention plugins
- Version catalog shared between main build and build-logic
- Multiple convention plugins: base-kotlin, spring-boot-app, spring-library
- Integration test suite convention
- At least 3 subprojects demonstrating different conventions

---

## Phase 4: Performance Optimization (Weeks 10-12)

**Goal**: Master build caching, configuration caching, and performance tuning.

### Week 10: Build Cache

**Local build cache** stores task outputs keyed by inputs. Enable in `gradle.properties`:

```properties
org.gradle.caching=true
```

**Understanding cache behavior**:

```bash
# See caching in action
./gradlew clean build
./gradlew clean build --build-cache  # Outputs from cache

# Debug cache misses
./gradlew build --build-cache -Dorg.gradle.caching.debug=true
```

**Making tasks cacheable**:

```kotlin
abstract class ProcessTemplates : DefaultTask() {
    @get:InputDirectory
    abstract val templates: DirectoryProperty
    
    @get:Input
    abstract val version: Property<String>
    
    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty
    
    @TaskAction
    fun process() { ... }
}
```

### Week 11: Configuration Cache

**Configuration cache** caches the entire configured task graph, skipping configuration phase on subsequent runs. This is Gradle's biggest recent performance improvement.

```properties
# gradle.properties
org.gradle.configuration-cache=true
```

**Common compatibility issues**:

```kotlin
// BAD: Captures Project at configuration time
tasks.register("bad") {
    doLast {
        println(project.version)  // Won't work with config cache
    }
}

// GOOD: Use providers
tasks.register("good") {
    val projectVersion = project.version
    doLast {
        println(projectVersion)
    }
}

// BETTER: Use lazy properties
abstract class MyTask : DefaultTask() {
    @get:Input
    abstract val version: Property<String>
}

tasks.register<MyTask>("best") {
    version.set(project.version.toString())
}
```

**Checking compatibility**:

```bash
./gradlew build --configuration-cache
# Review report at build/reports/configuration-cache/
```

### Week 12: Additional Performance Optimizations

**gradle.properties optimizations**:

```properties
# Parallel execution
org.gradle.parallel=true

# Build caching
org.gradle.caching=true

# Configuration cache
org.gradle.configuration-cache=true

# JVM tuning
org.gradle.jvmargs=-Xmx4g -XX:+UseParallelGC -XX:+HeapDumpOnOutOfMemoryError

# File system watching
org.gradle.vfs.watch=true

# Consistent file encoding
org.gradle.java.home.encoding=UTF-8
```

**Daemon tuning** for large projects:

```properties
org.gradle.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=512m -XX:+UseG1GC
```

**Avoiding configuration-time pitfalls**:

```kotlin
// BAD: File operations at configuration time
val files = fileTree("src").files.filter { it.name.endsWith(".kt") }

// GOOD: Lazy file collection
val files = fileTree("src").matching { include("**/*.kt") }
```

---

## Phase 5: Advanced Topics (Weeks 13-16)

**Goal**: Master custom tasks, plugins, and CI/CD integration.

### Week 13: Custom Tasks

**Task implementation patterns**:

```kotlin
// build-logic/src/main/kotlin/tasks/VerifyReadme.kt
abstract class VerifyReadme : DefaultTask() {
    @get:InputFile
    abstract val readme: RegularFileProperty
    
    @get:Input
    abstract val requiredSections: ListProperty<String>
    
    @get:OutputFile
    abstract val reportFile: RegularFileProperty
    
    init {
        requiredSections.convention(listOf("## Overview", "## Installation", "## Usage"))
        reportFile.convention(project.layout.buildDirectory.file("reports/readme-check.txt"))
    }
    
    @TaskAction
    fun verify() {
        val content = readme.get().asFile.readText()
        val missing = requiredSections.get().filter { section ->
            !content.contains(section)
        }
        
        if (missing.isNotEmpty()) {
            throw GradleException("README missing sections: $missing")
        }
        
        reportFile.get().asFile.writeText("README verification passed")
    }
}
```

**Registering in convention plugin**:

```kotlin
val verifyReadme = tasks.register<VerifyReadme>("verifyReadme") {
    readme.set(layout.projectDirectory.file("README.md"))
}

tasks.named("check") {
    dependsOn(verifyReadme)
}
```

### Week 14: Custom Binary Plugins (Kotlin)

For complex or reusable logic, create full plugins instead of precompiled scripts:

```kotlin
// build-logic/src/main/kotlin/plugins/ServicePlugin.kt
class ServicePlugin : Plugin<Project> {
    override fun apply(project: Project) {
        project.plugins.apply("org.springframework.boot")
        project.plugins.apply("kotlin-spring")
        
        val extension = project.extensions.create<ServiceExtension>("service")
        
        project.afterEvaluate {
            configureContainer(project, extension)
            configureTasks(project, extension)
        }
    }
    
    private fun configureContainer(project: Project, extension: ServiceExtension) {
        project.tasks.named<BootJar>("bootJar") {
            archiveBaseName.set(extension.serviceName)
        }
    }
    
    private fun configureTasks(project: Project, extension: ServiceExtension) {
        if (extension.enableHealthCheck.get()) {
            project.dependencies.add(
                "implementation",
                "org.springframework.boot:spring-boot-starter-actuator"
            )
        }
    }
}
```

**Plugin registration** in `build-logic/build.gradle.kts`:

```kotlin
gradlePlugin {
    plugins {
        create("servicePlugin") {
            id = "com.mycompany.service"
            implementationClass = "plugins.ServicePlugin"
        }
    }
}
```

### Week 15: Gradle with CI/CD

**GitHub Actions integration**:

```yaml
name: Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '21'
      
      - name: Setup Gradle
        uses: gradle/actions/setup-gradle@v4
        with:
          cache-read-only: ${{ github.ref != 'refs/heads/main' }}
      
      - name: Build
        run: ./gradlew build --configuration-cache
      
      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: '**/build/reports/tests/'
```

**Gradle Enterprise / Develocity** for build scans:

```kotlin
// settings.gradle.kts
plugins {
    id("com.gradle.develocity") version "3.17"
}

develocity {
    buildScan {
        termsOfUseUrl = "https://gradle.com/help/legal-terms-of-use"
        termsOfUseAgree = "yes"
        
        if (System.getenv("CI") != null) {
            publishing.onlyIf { true }
            tag("CI")
        }
    }
}
```

### Week 16: Testing Build Logic

**Testing convention plugins with TestKit**:

```kotlin
// build-logic/src/test/kotlin/ConventionPluginTest.kt
class ConventionPluginTest {
    @TempDir
    lateinit var projectDir: File
    
    @Test
    fun `spring-boot-conventions applies expected plugins`() {
        projectDir.resolve("build.gradle.kts").writeText("""
            plugins {
                id("spring-boot-conventions")
            }
        """.trimIndent())
        
        projectDir.resolve("settings.gradle.kts").writeText("")
        
        val result = GradleRunner.create()
            .withProjectDir(projectDir)
            .withPluginClasspath()
            .withArguments("tasks", "--all")
            .build()
        
        assertThat(result.output).contains("bootJar")
        assertThat(result.output).contains("bootRun")
    }
}
```

---

## Resource Summary

### Primary Resources

| Type | Resource | Cost | Notes |
|------|----------|------|-------|
| Official docs | [Gradle User Manual](https://docs.gradle.org/current/userguide/userguide.html) | Free | Comprehensive reference |
| Official docs | [Gradle Best Practices](https://docs.gradle.org/current/userguide/best_practices.html) | Free | New in 2024, essential reading |
| Course | [Tom Gregory's Gradle courses](https://tomgregory.com/) | ~$100-200 | Excellent practical focus |
| Video | TechWorld with Nana - Gradle Tutorial | Free | Good visual introduction |

### Reference Projects

- [Spring Boot](https://github.com/spring-projects/spring-boot/tree/main/buildSrc) - Convention plugins example
- [gradle/gradle](https://github.com/gradle/gradle) - Gradle's own build
- [kotlin-gradle-plugin-template](https://github.com/cortinico/kotlin-gradle-plugin-template) - Plugin development template

### Books (Note: Most are dated, prefer official docs)

- *Gradle in Action* (Manning) - Good fundamentals, but uses Groovy DSL
- Official documentation is the most current resource

---

## Final Capstone Project

Build a production-ready multi-module Spring Boot microservices template:

1. **Build logic** (included build):
   - `kotlin-common-conventions` - Base Kotlin configuration
   - `spring-boot-service-conventions` - Spring Boot applications
   - `spring-library-conventions` - Shared libraries
   - `integration-test-conventions` - Test suites
   - `docker-conventions` - Jib containerization

2. **Version catalog** with Spring Boot BOM integration

3. **Modules**:
   - `api-gateway` (Spring Cloud Gateway)
   - `user-service` (Spring Boot app)
   - `common` (shared library)
   - `test-fixtures` (shared test utilities)

4. **Features**:
   - Configuration cache compatible
   - Build cache enabled
   - GitHub Actions CI/CD
   - Build scan publishing
   - Custom verification tasks

5. **Documentation**:
   - ADR for build architecture decisions
   - README with build instructions

---

## Estimated Timeline

| Phase | Duration | Focus |
|-------|----------|-------|
| 1: Fundamentals | 3 weeks | Lifecycle, Kotlin DSL, dependencies |
| 2: Version Catalogs | 2 weeks | Modern dependency management |
| 3: Convention Plugins | 4 weeks | Multi-project architecture |
| 4: Performance | 3 weeks | Caching and optimization |
| 5: Advanced | 4 weeks | Custom plugins, CI/CD, testing |

**Total: 12-16 weeks** at 8-10 hours/week

This timeline can be compressed if you focus intensively on convention plugins (Phase 3), which is the highest-value skill for multi-project Spring Boot development.
