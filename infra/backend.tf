terraform {
  backend "gcs" {
    bucket = "cloudrunantigravity-tfstate"
    prefix = "terraform/state"
  }
}
