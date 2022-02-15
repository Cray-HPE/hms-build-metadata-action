# hms-build-metadata-action

- [hms-build-metadata-action](#hms-build-metadata-action)
  - [Action inputs](#action-inputs)
  - [Action outputs](#action-outputs)
  - [Example usage:](#example-usage)
    - [Helm chart](#helm-chart)
    - [Docker container image](#docker-container-image)
  - [Release model](#release-model)

The hms-build-metadata-action provides the following functionality:
1.  Determines if the current Github Action workflow run is destined to create stable or unstable artifacts. 
    What constitutes a stable build is configurable via the `stable-strategy` input:

    | Stable Strategy | Description
    | --------------- | ----------- 
    | `branch`        | Match the branch that triggered the workflow run against the value provided `stable-branch-regex` input. If it matches the regex the build is considered stable, other unstable. This is typically used when building the HMS Helm charts.
    | `tag`           | The build will be considered stable if the Github Action workflow run was triggered by the creation of a Git tag. This is typically used when building HMS container images.
    | `always`        | Always treat the workflow run as stable. This is not normally used, but used to aid with debugging.
    | `never`         | Always treat the workflow run as unstable. This is not normally used, but used to aid with debugging.

2. Generates version suffixes for the build.
   1. Helm Charts
      1. For stable builds no version suffix is generated.
      2. For unstable builds the version suffix is in the form of `-timestamp+gitsha`. For example: `-2.0.4-20211213150940+c3db9cac` 
   2. Docker container images
      1. Stable and unstable builds always have a build suffix generated in the form of `-timestamp.gitsha`. For example: `-20220201202912.1ad88cd`
         > Note that Docker container image names do not allow the `+` character in image names, so `.` is being used instead. 

This Github action is implemented as a [composite action](https://docs.github.com/en/actions/creating-actions/creating-a-composite-action). This action performs steps:
1. Install Python 3 on the Github Action runner.
2. Execute the [generate_build_metadata.py](generate-build-metadata/generate_build_metadata.py) script directly on the Github Action runner.

## Action inputs
| Name                    | Data Type | Required Field | Default value | Description
| ----------------------- | --------- | -------------- | ------------- | -----------
| `stable-strategy`       | `string`  | Optional       | `branch`      | The method for determining a stable branch. Choices: `branch`, `tag`, `always`, `never`
| `stable-branches-regex` | `string`  | Optional       | `master`      | Regular expression to determine a stable branch

## Action outputs
| Name                    | Data Type           | Example Value             | Description
| ----------------------- | ------------------- | ------------------------- | -------------
| `is-stable`             | stringified boolean | `"true"`                  | Is the build considered stable.
| `timestamp`             | string              | `20220201202912`          | Timestamp of the build.
| `git-sha`               | string              | `1ad88cd`                 | The short Git SHA of the commit that triggered the build.
| `git-branch`            | string              | `feature/foo`             | The Git branch that triggered the build.
| `helm`                  | string              | `-20220201202912+1ad88cd` | The Helm version suffix for the build. For stable builds this value will be empty.
| `docker`                | string              | `-20220201202912.1ad88cd` | The Docker version suffix for the build.
## Example usage:
### Helm chart
The following is a contrived example of how to use the generate-build-metadata action to generate build metadata for Helm charts. For a production use of this action see the [build_and_release_charts.yaml workflow in the hms-build-chart-workflows repository](https://github.com/Cray-HPE/hms-build-chart-workflows/blob/main/.github/workflows/build_and_release_charts.yaml).

```yaml
name: Build and Publish Helm charts
on:
  workflow_call:
    inputs:
      runs-on:
        type: string
        required: false
        default: ubuntu-latest
      target-branch:
        type: string
        required: false
        default: "master"
jobs:
  build_and_release:
    name: Build and Publish Helm charts
    runs-on: ${{ inputs.runs-on }}
    steps:
    # Run the action
    - name: Generate build metadata
      uses: Cray-HPE/hms-build-metadata-action/generate-build-metadata@v1
      id: build-meta
      with:
        stable-strategy: branch
        stable-branches-regex: ${{ inputs.target-branch }}
    
    # Now do something useful with action outputs!
    - name: Determine full chart version
      shell: bash
      with:
        HELM_VERSION_SUFFIX: ${{ steps.build-meta.outputs.helm }}
      run: |
        VERSION="0.0.1$HELM_VERSION_SUFFIX"
        echo "$VERSION"

    - name: Run this step only if the build is stable
      shell: bash
      run: | 
        echo "This is a stable artifact!"
      if: fromJSON(steps.build-meta.outputs.is-stable)
```

### Docker container image
The following is a contrived example of how to use the generate-build-metadata action to generate build metadata for Docker container images. For a production use of this action see the [build_and_release_image.yaml workflow in the hms-build-image-workflows repository](https://github.com/Cray-HPE/hms-build-image-workflows/blob/main/.github/workflows/build_and_release_image.yaml).
```yaml
name: Build and Publish Docker images
on:
  workflow_call:
    inputs:
      runs-on:
        description: The type of machine to run the job on.
        type: string
        required: false
        default: ubuntu-latest
jobs:
  build_and_release:
  # Run the action
  - name: Generate build metadata
    uses: Cray-HPE/hms-build-metadata-action/generate-build-metadata@v1
    id: build-metadata
    with:
      stable-strategy: tag

  # Now do something useful with action outputs!
  - name: Determine container image name and tag
    id: image-meta
    run: |
      # Retrieve the version from the .version file, and append the build metadata to it.
      STABLE_STRING=${{ fromJSON(steps.build-metadata.outputs.is-stable) && 'stable' || 'unstable' }}
      DOT_VERSION=$(cat .version)
      TAG=$DOT_VERSION${{ steps.build-metadata.outputs.docker }}
      
      echo ".version: $DOT_VERSION"
      echo "Stable string: $STABLE_STRING"
      echo "Container image tag: $TAG"
```

## Release model

When you make changes you should tag the code branch with an vX.Y.Z semver and move/create the vX tag.

the vX tag (eg v1) is used by the 'invoking' workflows.  The contract is that vX(n) MUST be backwards compatible.  
the vX.Y.Z tag is used to distinguish code changes as a release.