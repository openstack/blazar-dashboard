pipeline {
  agent any

  options {
    copyArtifactPermission(projectNames: 'horizon-kolla/*')
  }

  stages {
    stage('package') {
      steps {
        dir('dist') {
          deleteDir()
        }
        sh 'python setup.py sdist'
        sh 'find dist -type f -exec cp {} dist/blazar-dashboard.tar.gz \\;'
        archiveArtifacts(artifacts: 'dist/blazar-dashboard.tar.gz', onlyIfSuccessful: true)
      }
    }
  }
}
